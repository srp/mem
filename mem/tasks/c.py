import subprocess
from subprocess import PIPE
import mem
from mem.nodes import File

@mem.with_env(CFLAGS=[])
@mem.task
def make_depends(m, source, CFLAGS=[]):
    m.add_dep(File(source))
    args = ["gcc"] + CFLAGS + ["-M", "-o", "-", source]
    print " ".join(args)
    p = subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
    out = p.stdout.readlines()
    if p.wait() != 0:
        fail()
    deps = []

    # ignore the "file.o:" prefix on the first line
    deps.extend([File(s) for s in out.pop(0).split()[1:-1]])

    if len(out) == 0:
        return deps

    # the last line doesn't have the "\" suffix
    deps.extend([File(s) for s in out.pop().split()])

    for l in out:
        deps.extend([File(s) for s in l.split()[:-1]])

    return deps

@mem.with_env(CFLAGS=[])
@mem.task
def obj(m, target, source, CFLAGS=[]):
    m.add_dep(File(source))
    m.add_deps(make_depends(source, CFLAGS=CFLAGS))
    args = ["gcc"] +  CFLAGS + ["-c", "-o", target, source]
    print " ".join(args)
    if subprocess.call(args) != 0:
        mem.fail()
    return File(target)

@mem.with_env(CFLAGS=[])
@mem.task
def prog(m, target, objs, CFLAGS=[]):
    m.add_deps(objs)
    args = ["gcc", "-o", target] + CFLAGS + [o.path for o in objs]
    print " ".join(args)
    if subprocess.call(args) != 0:
        mem.fail()
    return File(target)
