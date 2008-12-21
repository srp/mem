import subprocess
import mem
from mem.nodes import File

@mem.task
def make_depends(m, source):
    return popen(["gcc", "-M", "-o", "-", File(source)]).readlines()

@mem.task
def obj(m, target, source):
    m.add_dep(File(source))
    args = ["gcc", "-c", "-o", target, source]
    print " ".join(args)
    assert subprocess.call(args) == 0
    return File(target)

@mem.task
def prog(m, target, *objs):
    m.add_deps(objs)
    args = ["gcc", "-o", target] + [o.path for o in objs]
    print " ".join(args)
    assert subprocess.call(args) == 0
    return File(target)
