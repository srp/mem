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

    mem.util.ensure_file_dir(target)
    if mem.util.quietly_execute("Building Library", target, args) != 0:
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
