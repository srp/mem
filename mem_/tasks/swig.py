import os.path
import re
import subprocess
from subprocess import PIPE
import mem


re_import = re.compile('[ \t]*[%,#][ \t]*(?:include|import)[ \t]*'
                       '(?:<|")([^>"]+)(?:>|")')
# Match '%module test', as well as '%module(directors="1") test'
re_module = re.compile(r'%module(?:\s*\(.*\))?\s+(.+)')

def make_depends(c, target, source, CFLAGS, CPPPATH):
    files = []
    for path in CPPPATH:
        file = mem.util.search_file(str(source), path)
        if file:
            files.append(file)
            if file.endswith(".h"):
                files.append(c.make_depends(target, file, CFLAGS, CPPPATH))
                break
            elif file.endswith(".i"):
                for name in re_import.findall(open(file).read()):
                    return make_depends(c, target, name, CFLAGS, CPPPATH)

                break

    return mem.nodes.DepFiles(mem.util.flatten(files))

def find_produces(c, target, source, SWIGFLAGS, CFLAGS, CPPPATH):
    ret = []
    mem.add_dep(make_depends(c, target, source,
                             CFLAGS, ["./"] + CPPPATH))
    print source
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


@mem.util.with_env(SWIGFLAGS=[], CFLAGS=[], CPPPATH=[], c=None)
@mem.memoize
def to_c(target, source, SWIGFLAGS, CFLAGS, CPPPATH, c):
    mem.add_dep(mem.util.convert_to_file(source))
    targets = find_produces(c, target,
                            source, SWIGFLAGS, CFLAGS, CPPPATH)
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




def obj(sources, env=None, build_dir = None, c=None,
        SWIGFLAGS=None, CFLAGS=None, CPPPATH=None):
    if not type(sources) == list:
        sources = [sources]

    nslist = mem.util.flatten(sources)
    BuildDir = mem.util.get_build_dir(env, build_dir)
    nslist = mem.util.flatten(sources)

    cflags = env.get_override("CFLAGS", CFLAGS)

    c = env.get_override("c", c)
    targets = []
    for source in nslist:
        (name, ignore) = os.path.splitext(str(source))
        target = os.path.join(BuildDir, name + "_wrap.c")
        targets.append(to_c(target, source,
                            env.get_override("SWIGFLAGS", SWIGFLAGS),
                            env.get_override("SWIG_CFLAGS", cflags),
                            env.get_override("CPPPATH", CPPPATH),
                            c))
        targets.append(target)

    ntargets = []
    for target in mem.util.flatten(targets):
        if str(target).endswith(".c"):
            ntargets.append(env.c.obj(target, env=env, CFLAGS=cflags))
        else:
            ntargets.append(target)

    return mem.util.convert_to_files(mem.util.flatten(ntargets))

