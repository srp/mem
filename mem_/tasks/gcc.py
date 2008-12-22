import os
import subprocess
from subprocess import PIPE

import mem

File = mem.nodes.File

@mem.with_env(CFLAGS=[])
@mem.task
def make_depends(source, CFLAGS=[]):
    mem.add_dep(File(source))
    args = ["gcc"] + CFLAGS + ["-M", "-o", "-", source]
    print " ".join(args)
    p = subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
    deps = p.stdout.read().split()
    if p.wait() != 0:
        mem.fail()

    deps = deps[1:] # first element is the target (eg ".o"), drop it
    return [File(dep) for dep in deps if dep != '\\']

@mem.with_env(CFLAGS=[])
@mem.task
def t_obj(target, source, CFLAGS=[]):
    if not os.path.exists(source):
        mem.fail("%s does not exist" % source)

    mem.add_dep(File(source))
    mem.add_deps(make_depends(source, CFLAGS=CFLAGS))
    args = ["gcc"] +  CFLAGS + ["-c", "-o", target, source]
    print " ".join(args)
    if subprocess.call(args) != 0:
        mem.fail()
    return File(target)

@mem.with_env(CFLAGS=[])
@mem.task
def t_prog(target, objs, CFLAGS=[]):
    mem.add_deps(objs)
    args = ["gcc", "-o", target] + CFLAGS + [o.path for o in objs]
    print " ".join(args)
    if subprocess.call(args) != 0:
        mem.fail()
    return File(target)

def obj(source_list, env=None, build_dir = None):
    """ Take a list of sources and convert them to a correct object file """
    if not type(source_list) == list:
        source_list = [source_list]
    nslist = mem.util.flatten(source_list)
    BuildDir = mem.util.get_build_dir(env, build_dir)
    targets = []
    for source in nslist:
        (name, ignore) = os.path.splitext(source)
        target = os.path.join(BuildDir, name + ".o")
        t_obj(target, source, env.CFLAGS)
        targets.append(File(target))

    return targets

def prog(target, objs, env=None, build_dir = None):
    """ Convert the list of objects into a program given the cflags """
    nobjs = mem.util.flatten(objs)
    BuildDir = mem.util.get_build_dir(env, build_dir)
    ntarget = os.path.join(BuildDir, target)
    t_prog(ntarget, nobjs, env.CFLAGS)

