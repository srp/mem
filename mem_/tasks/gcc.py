import os
import subprocess
from subprocess import PIPE

import mem

File = mem.nodes.File
DepFiles = mem.nodes.DepFiles

def make_depends(target, source, CFLAGS, CPPPATH):
    mem.add_dep(mem.util.convert_to_file(source))
    includes = ["-I" + path for path in CPPPATH]
    args = mem.util.convert_cmd(["gcc"] + CFLAGS +
                                ["-I" +
                                 os.path.dirname(target)] +
                                includes + ["-M", "-o", "-", source])
    print " ".join(args)
    p = subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
    deps = p.stdout.read().split()
    if p.wait() != 0:
        mem.fail()

    deps = deps[1:] # first element is the target (eg ".o"), drop it
    return DepFiles(dep for dep in deps if dep != '\\')

@mem.util.with_env(CFLAGS=[], CPPPATH=[])
@mem.memoize
def t_obj(target, source, CFLAGS, CPPPATH):
    if not os.path.exists(str(source)):
        mem.fail("%s does not exist" % source)

    mem.add_dep(mem.util.convert_to_file(source))
    mem.add_dep(make_depends(target, source, CFLAGS=CFLAGS, CPPPATH=CPPPATH))
    includes = ["-I" + path for path in CPPPATH]
    args = mem.util.convert_cmd(["gcc"] +  CFLAGS + includes +
                                ["-I" +
                                 os.path.dirname(target)] +
                                ["-c", "-o", target, source])
    print " ".join(args)

    mem.util.ensure_file_dir(target)
    if subprocess.call(args) != 0:
        mem.fail()
    return File(target)

@mem.util.with_env(CFLAGS=[], LIBS=[], LIBPATH=[])
@mem.memoize
def t_prog(target, objs, CFLAGS, LIBS, LIBPATH):
    mem.add_deps(objs)

    npaths = map(lambda a: "-L" + str(a), LIBPATH)
    nlibs = map(lambda a: "-l" + str(a), LIBS)

    args = mem.util.convert_cmd(["gcc", "-o", target] + CFLAGS +
                                npaths + nlibs + [o.path for o in objs])

    print " ".join(args)

    mem.util.ensure_file_dir(target)
    if subprocess.call(args) != 0:
        mem.fail()
    return File(target)

def obj(source_list, env=None, build_dir = None,
        CFLAGS = None, CPPPATH = None):
    """ Take a list of sources and convert them to a correct object file """
    if not type(source_list) == list:
        source_list = [source_list]
    nslist = mem.util.flatten(source_list)
    BuildDir = mem.util.get_build_dir(env, build_dir)
    targets = []
    for source in nslist:
        (name, ignore) = os.path.splitext(str(source))
        target = os.path.join(BuildDir, name + ".o")
        t_obj(target, source,
              env.get_override("CFLAGS", CFLAGS),
              env.get_override("CPPPATH", CPPPATH))
        targets.append(File(target))

    return targets

def prog(target, objs, env=None, CFLAGS=[], LIBS=[], LIBPATH=[],
         build_dir = None):
    """ Convert the list of objects into a program given the cflags """
    nobjs = mem.util.flatten(objs)
    BuildDir = mem.util.get_build_dir(env, build_dir)
    ntarget = os.path.join(BuildDir, target)
    t_prog(ntarget, nobjs, env.get_override("CFLAGS", CFLAGS),
           env.get_override("LIBS", LIBS),
           env.get_override("LIBPATH", LIBPATH))
    return File(ntarget)
