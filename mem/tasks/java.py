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
