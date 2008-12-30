import os
import sys
import commands
import mem

@mem.memoize
def t_asciidoc(target, source):
    """ Runs asciidoc compiler on specified files """
    mem.add_dep(mem.util.convert_to_file(source))
    cmd = "asciidoc --out-file=%s %s" % (str(target), str(source))
    print cmd
    (stat, out) = commands.getstatusoutput(cmd)
    if stat:
        mem.fail(cmd + ":" + out)

    return mem.nodes.File(target)


def asciidoc(source, build_dir=None, env=None):
    if not isinstance(source, list):
        source = [source]

    sources = mem.util.flatten(source)
    BuildDir = mem.util.get_build_dir(env, build_dir)

    out = []
    for src in sources:
        (name, ext) = os.path.splitext(str(src))
        target = os.path.join(BuildDir, name + ".html")

        out.append(t_asciidoc(target, src))

    return out
