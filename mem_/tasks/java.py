import os
import subprocess

import mem

File = mem.nodes.File

@mem.util.with_env(JAVA_FLAGS=[])
@mem.memoize
def _compile(sources, BuildDir, JAVA_FLAGS):
    args = ["javac", "-d", BuildDir] + JAVA_FLAGS + sources
    print " ".join(args)
    if subprocess.call(args) != 0:
        mem.fail()
    return [File(os.path.join(BuildDir, os.path.splitext(source)[0] + ".class"))
            for source in sources]


def compile(sources, env=None, build_dir=None, **kwargs):
    BuildDir = mem.util.get_build_dir(env, build_dir)

    if not type(sources) == list:
        sources = [sources]
    else:
        sources = [os.path.join(os.getcwd(), str(source))
                   for source in mem.util.flatten(sources)]
        sources.sort()

    return _compile(sources, BuildDir, **kwargs)
