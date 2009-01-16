import os
import sys
import commands
import mem
import subprocess
from subprocess import PIPE

@mem.util.with_env(ASCIIDOC_FLAGS=[])
@mem.memoize
def t_asciidoc(target, source, ASCIIDOC_FLAGS):
    """ Runs asciidoc compiler on specified files """
    mem.add_dep(mem.util.convert_to_file(source))

    cmd = mem.util.convert_cmd(["asciidoc","-o",target]+ASCIIDOC_FLAGS+[source])

    print " ".join(cmd)

    mem.util.ensure_file_dir(target)
    if subprocess.call(cmd) != 0:
        mem.fail()

    return mem.nodes.File(target)


def asciidoc(source, build_dir=None, env=None, ASCIIDOC_FLAGS=[]):
    if not isinstance(source, list):
        source = [source]

    sources = mem.util.flatten(source)
    BuildDir = mem.util.get_build_dir(env, build_dir)

    out = []
    for src in sources:
        (name, ext) = os.path.splitext(str(src))
        target = os.path.join(BuildDir, name + ".html")

        out.append(t_asciidoc(target, src, env=env))

    return out
