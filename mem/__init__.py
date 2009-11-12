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

import cPickle as pickle


# TODO: this function uses private functions from mem, but 
# must be outside of mem to be used as a decorator even before
# the mem singleton was created.
def memoize(taskf):
    def f(*args, **kwargs):
        mem = Mem.instance()
        if mem is None:
            raise RuntimeError("Mem Singleton has not yet been created")

        tchash = mem.get_hash(taskf.__name__, taskf.__module__,
                               args, kwargs)
        try:
            f = open(mem._deps_path(tchash), "rb")
            deps = pickle.load(f)
            f.close()

            f = open(mem._results_path(mem.get_hash(tchash, deps)), "rb")
            result = pickle.load(f)
            f.close()

            def restore(o):
                if (hasattr(o, "restore")):
                    o.restore()
                elif (hasattr(o, "__iter__")):
                    for el in o:
                        restore(el)

            restore(result)

            mem.deps_stack().add_deps_if_in_memoize(deps)
            return result
        except IOError:
            return mem._run_task(taskf, args, kwargs, tchash)

    f.__module__ = taskf.__module__
    return f


def _find_root():
    d = os.path.abspath(os.curdir)
    while (not os.path.exists(os.path.join(d, "MemfileRoot"))):
        if d == "/":
            sys.stderr.write("No 'MemfileRoot' found!\n")
            sys.exit(1)
        d = os.path.dirname(d)
    return d

# TODO: stupid name, rename this function!
def do_build(root, build_callable):
    os.chdir(root)
    mem = Mem(root)
    try:
        build_callable()
    except KeyboardInterrupt:
        print "-" * 50
        print "build interrupted."

def import_memfile(f):
    return util.import_module(f, f)

def main():
    sys.path.append("./")
    root = _find_root()
    mfr_mod = import_memfile(root + os.path.sep + "MemfileRoot")
    do_build(root, mfr_mod.build)

