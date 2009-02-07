# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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

        out.append(t_asciidoc(target, src,
                              env=env, ASCIIDOC_FLAGS=ASCIIDOC_FLAGS))

    return out
