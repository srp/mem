import os.path
import re
import subprocess
from subprocess import PIPE
import mem

# Match '%module test', as well as '%module(directors="1") test'
re_module = re.compile(r'%module(?:\s*\(.*\))?\s+(.+)')

def make_depends(source, SWIGFLAGS):
    args = mem.util.convert_cmd(["swig"] + SWIGFLAGS +
                                ["-M", source])
    print " ".join(args)
    p = subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
    deps = p.stdout.read().split()
    if p.wait() != 0:
        mem.fail()

    deps = deps[1:] # first element is the target (eg ".c"), drop it
    return [dep for dep in deps if dep != '\\']

def find_produces(target, source, SWIGFLAGS):
    ret = []
    src_data = open(str(source)).read()
    output = re_module.findall(src_data)
    outdir = os.path.dirname(target)
    mnames = None
    if "-python" in SWIGFLAGS and "-noproxy" not in SWIGFLAGS:
            if mnames is None:
                mnames = re_module.findall(open(str(source)).read())
            ret.extend(map(lambda m, d=outdir:
                                  os.path.join(outdir, m + ".py"), mnames))
    if "-java" in SWIGFLAGS:
        if mnames is None:
            mnames = re_module.findall(open(src).read())
            java_files = map(lambda m: [m + ".java", m + "JNI.java"], mnames)
            java_files = mem.util.flatten(java_files)
        if outdir:
            java_files = map(lambda j, o=outdir:
                                  os.path.join(o, j), java_files)
            java_files = map(env.fs.File, java_files)


            ret.extend(java_files)
    return ret


@mem.util.with_env(SWIGFLAGS=[])
@mem.memoize
def to_c(target, source, SWIGFLAGS):
    mem.add_dep(mem.util.convert_to_file(source))
    mem.add_deps([mem.nodes.File(f) for f in make_depends(source, SWIGFLAGS)])

    targets = find_produces(target, source, SWIGFLAGS)
    targets.append(target)
    args = mem.util.convert_cmd(['swig',
                                 '-o',
                                 target,
                                 '-outdir',
                                 os.path.dirname(target)] +
                                SWIGFLAGS + [source])

    print " ".join(args)

    mem.util.ensure_file_dir(target)
    p = subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
    if p.wait() != 0:
        mem.fail()

    return [mem.nodes.File(f) for f in targets]


def obj(sources, env=None, build_dir=None, **kwargs):
    if not type(sources) == list:
        sources = [sources]

    env = env.copy()
    env.update(kwargs)

    nslist = mem.util.flatten(sources)
    BuildDir = mem.util.get_build_dir(env, build_dir)
    nslist = mem.util.flatten(sources)

    targets = []
    threads = []
    for source in nslist:
        (name, ignore) = os.path.splitext(str(source))
        target = os.path.join(BuildDir, name + "_wrap.c")
        t = mem.util.Runable(to_c, target, source, env=env)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
        targets.extend(t.result)

    ntargets = []
    ctargets = []
    for target in mem.util.flatten(targets):
        if str(target).endswith(".c"):
            ctargets.append(target)
        else:
            ntargets.append(target)

    ntargets.extend(env.c.obj(ctargets, env=env, CFLAGS=env.SWIG_CFLAGS))


    return mem.util.convert_to_files(mem.util.flatten(ntargets))
