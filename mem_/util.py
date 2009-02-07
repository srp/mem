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

from string import split
import os
import imp
import sys
from threading import Thread, Semaphore

def get_build_dir(env, arg_func):
    """ return a valid build directory given the environment """
    import mem

    if arg_func and type(arg_func) == str:
        return arg_func
    elif arg_func:
        return arg_func(env)

    if not env:
        return mem.cwd

    try:
        func = env.BUILD_DIR_FUNC

        if func:
            return func(env)
    except AttributeError:
        pass

    try:
        if not env.BUILD_DIR:
            return src_dir
    except AttributeError:
        pass

    root = mem.root
    src_dir = mem.cwd

    if not src_dir.startswith(root):
        mem.fail("source dir (%s) is not a subdir of root (%s) "
                 "unable to generate a build path" % src_dir, root)

    sub_dir = src_dir[len(root) + 1:]


    dir = os.path.join(root, env.BUILD_DIR, sub_dir)

    try:
        os.makedirs(dir)
    except OSError:
        pass

    return dir


def flatten(l, ltypes=(list, tuple)):
    """ Flatten a list type into single list """
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)


def convert_to_files(src_list):
    """ Convert a list of mixed strings/files to files """
    from mem_.nodes import File
    nlist = []
    for src in src_list:
        if isinstance(src, File):
            nlist.append(src)
        else:
            nlist.append(File(src))
    return nlist

def convert_to_file(src):
    from mem_.nodes import File
    if isinstance(src, File):
        return src
    else:
        return File(src)

def convert_cmd(lst):
    return [str(a) for a in lst]

def search_file(filename, paths):
    """Given a search path, find file
    """
    if os.path.exists(filename):
        return filename

    if isinstance(paths, str):
        paths = paths.split(os.path.pathsep)

    for path in paths:
        fp = os.path.join(path, filename)
        if os.path.exists(fp):
            return fp
    return None


def with_env(**kwargs):
    def decorator(f):
        def new_f(*args, **fkwargs):
            if fkwargs.has_key("env"):
                fenv = fkwargs.pop("env")
                for k in kwargs.keys():
                    if not fkwargs.has_key(k) or not fkwargs[k]:
                        if fenv and fenv.has_key(k):
                            fkwargs[k] = fenv[k]
                        else:
                            fkwargs[k] = kwargs[k]
            return f(*args, **fkwargs)
        new_f.__module__ = f.__module__
        return new_f
    return decorator

def ensure_file_dir(path):
    try:
        os.makedirs(os.path.dirname(path))
    except OSError:
        pass

def ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError:
        pass

def import_module(name, fname=None):
    if not fname:
        fname = name + ".py"
    m = imp.new_module(os.path.basename(name))
    m.__file__ = fname
    execfile(fname, m.__dict__, m.__dict__)
    return m


class Runable(Thread):
    def __init__(self, f, *args, **kwargs):
        Thread.__init__(self)
        self.f = f
        self.args = args
        self.kwargs = kwargs

    def run(self):
        import mem
        if not mem.thread_limit == None:
            mem.thread_limit.acquire()

        if mem.failed:
            sys.exit(1)

        self.result = self.f(*(self.args), **(self.kwargs))

        if not mem.thread_limit == None:
            mem.thread_limit.release()

    def join(self):
        import mem

        if mem.failed:
            sys.exit(1)

        Thread.join(self)

        if mem.failed:
            sys.exit(1)
