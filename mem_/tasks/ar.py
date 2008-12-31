import subprocess
from subprocess import PIPE
import os
import mem


@mem.util.with_env(ARCMD="ar", ARARGS=["rc"])
@mem.memoize
def t_ar(target, sources, ARARGS, ARCMD):
    if not isinstance(sources, list):
        sources = [sources]
    mem.add_deps(sources)

    args = mem.util.convert_cmd([ARCMD] + ARARGS + [target] + sources)

    print " ".join(args)

    mem.util.ensure_file_dir(target)
    if subprocess.call(args) != 0:
        mem.fail()

    return mem.nodes.File(target)


def ar(target, sources, LIBSUFFIX=".a", LIBPREFIX="lib",
       build_dir=None, env=None):
    BuildDir = mem.util.get_build_dir(env, build_dir)
    if not target[-2:] == LIBSUFFIX:
        target += LIBSUFFIX
    if not target[0:3] == LIBPREFIX:
        target = LIBPREFIX + target

    ntarget = os.path.join(BuildDir, target)

    return t_ar(ntarget, sources, env=env)
