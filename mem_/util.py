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
import subprocess
import re

RED    = chr(27) + "[31m"
GREEN  = chr(27) + "[32m"
YELLOW = chr(27) + "[33m"
RESET  = chr(27) + "[0m"

def quiet_level():
    try:
        quiet = int(os.environ['MEM_QUIET'])
    except KeyError:
        quiet = 0
    return quiet

def _is_dumb_term_():
    try:
        return os.environ['TERM'] in ("emacs", "dumb")
    except KeyError:
        return True

# MEM_COLOR_LEVEL=0 to explicitly disable coloring
def _should_color_():
    try:
        mem_color_level = int(os.environ['MEM_COLOR_LEVEL'])
    except KeyError:
        # By default enable coloring
        mem_color_level = 1
    return mem_color_level > 0 and not _is_dumb_term_()

def get_color_status(returncode):
    if returncode != 0:
        status = "ERROR"
        color = RED
    else:
        status = "OK"
        color = GREEN

    if _should_color_():
        status = "[%s%s%s]" % (color, status, RESET)
    else:
        status = "[%s]" % status

    return status.rjust(16)

def _mark_output_(s):
    if _should_color_():
        s = re.sub("warning:", "%swarning:%s" % (YELLOW, RESET), s)
        s = re.sub("error:", "%serror:%s" % (RED, RESET), s)
        s = re.sub("Warning", "%sWarning%s" % (YELLOW, RESET), s)

    return s

def _open_pipe_(args, shell=False):
    p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell)

    (stdoutdata, stderrdata) = p.communicate()

    return (p.returncode, stdoutdata, stderrdata)

def make_depends(prefix, source, args):
    (returncode, stdoutdata, stderrdata) = \
        run_return_output_no_print(prefix, source, _open_pipe_, args)

    deps = stdoutdata.split()

    sys.stdout.write(_mark_output_(stderrdata))

    if returncode != 0:
        import mem
        mem.fail()

    deps = deps[1:] # first element is the target (eg ".c"), drop it
    return [dep for dep in deps if dep != '\\']

def run_return_output_no_print(prefix, source, fun, *args, **kwargs):
    '''
    run commands specified in args (a sequence or string), optionally in a
    shell, and returns a tuple (resultcode, stdoutdata, stderrdata), where
    stdoutdata and stderrdata are strings.

    prefix will be truncated and right-justified to 25 characters
    source
    '''
    e = None
    try:
        (returncode, stdoutdata, stderrdata) = fun(*args, **kwargs)
    finally:
        if quiet_level() > 0:
            print get_color_status(returncode), prefix.rjust(25),
            print os.path.basename(source)
        elif fun == _open_pipe_:
            if isinstance(args[0], (str, unicode)):
                print args[0]
            else:
                print " ".join(args[0])
        elif args or kwargs:
            allargs = [repr(a) for a in args] + \
                ["%s=%s" % (str(k), repr(v))
                 for k,v in kwargs.iteritems()]
            print "%s(%s)" % (fun.__name__, ", ".join(allargs))
        else:
            print "%s()" % fun.__name__

    return (returncode, stdoutdata, stderrdata)

def run_return_output(prefix, source, fun, *args):
    '''
    run commands specified in args (a sequence or string), optionally in a
    shell, and returns a tuple (resultcode, stdoutdata, stderrdata), where
    stdoutdata and stderrdata are strings.

    As a side effect, it also dump both stdoutdata and stderrdata to
    sys.stdout.

    prefix will be truncated and right-justified to 25 characters
    source
    '''
    (returncode, stdoutdata, stderrdata) = \
        run_return_output_no_print(prefix, source, fun, *args)
    sys.stdout.write(_mark_output_(stdoutdata))
    sys.stdout.write(_mark_output_(stderrdata))
    if returncode != 0:
        import mem
        mem.fail()

    return (returncode, stdoutdata, stderrdata)

def run(prefix, source, args, shell=False):
    '''
    run commands specified in args (a sequence or string), optionally in a
    shell, and returns the result code.

    prefix will be truncated and right-justified to 25 characters
    source
    '''
    return run_return_output(prefix, source, _open_pipe_, args, shell)[0]

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
        if env.BUILD_DIR_FUNC:
            return env.BUILD_DIR_FUNC(env)
    except AttributeError:
        pass

    if "BUILD_DIR" not in env or not env.BUILD_DIR:
        return mem.cwd

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


class Env(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("'Env' object has no attribute '%s'" % key)

    def __setattr__(self, key, val):
	self[key] = val

    def __repr__(self):
        return "Env(" + " ".join("%s=%s" % (k, repr(v))
                                 for k,v in self.items()) + ")"

    def __str__(self):
        return repr(self)

    def copy(self):
        return Env(dict.copy(self))

    def replace(self, **kwargs):
        for key, value in kwargs.items():
            if type(value) == str:
                self[key] = value % self
            elif type(value) == list:
                nlist = []
                for el in value:
                    if type(el) == str:
                        nlist.append(el % self)
                    else:
                        nlist.append(el)
                self[key] = nlist
            else:
                self[key] = value

    def subst(self, value):
        return value % self
