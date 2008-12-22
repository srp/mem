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
def obj(target, source, CFLAGS=[]):
    mem.add_dep(File(source))
    mem.add_deps(make_depends(source, CFLAGS=CFLAGS))
    args = ["gcc"] +  CFLAGS + ["-c", "-o", target, source]
    print " ".join(args)
    if subprocess.call(args) != 0:
        mem.fail()
    return File(target)

@mem.with_env(CFLAGS=[])
@mem.task
def prog(target, objs, CFLAGS=[]):
    mem.add_deps(objs)
    args = ["gcc", "-o", target] + CFLAGS + [o.path for o in objs]
    print " ".join(args)
    if subprocess.call(args) != 0:
        mem.fail()
    return File(target)
