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

import os, sys

import tasks, util, nodes

from _mem import Mem

def memoize(*args, **kwargs):
    return Mem.instance().memoize(*args, **kwargs)

def _find_root():
    d = os.path.abspath(os.curdir)
    while (not os.path.exists(os.path.join(d, "MemfileRoot"))):
        if d == "/":
            sys.stderr.write("No 'MemfileRoot' found!\n")
            sys.exit(1)
        d = os.path.dirname(d)
    return d

def main():
    sys.path.append("./")
    root = _find_root()
    os.chdir(root)
    mem = Mem(root)
    print "Creating: singleton!: " 
    mfr_mod = mem.import_memfile("MemfileRoot")
    try:
        mfr_mod.build()
    except KeyboardInterrupt:
        print "-" * 50
        print "build interrupted."

