import cPickle as pickle
from cpu_count import cpu_count
import imp
import os
import sha
import sys
import types

import util

import threading

MEM_DIR = ".mem"
DEPS_DIR = "deps"
RESULTS_DIR = "results"
BLOB_DIR = "blob"

class DepsStack(object):
    def __init__(self):
        self.deps = []

    def call_start(self):
        self.deps.append([])

    def call_finish(self):
        return self.deps.pop()

    def add_dep(self, d):
        self.deps[-1].append(d)

    def add_deps(self, ds):
        self.deps[-1].extend(ds)


class Mem(object):
    def __init__(self, root):
        self.root = root
        self.cwd = root

        memdir = os.path.join(root, MEM_DIR)
        if not os.path.exists(memdir):
            os.mkdir(memdir)

        self.deps_dir = os.path.join(memdir, DEPS_DIR)
        self.results_dir = os.path.join(memdir, RESULTS_DIR)
        self.blob_dir = os.path.join(memdir, BLOB_DIR)

        self.thread_limit = threading.Semaphore(cpu_count() * 2)
        self.local = threading.local()

    def __setup__(self):
        import mem_.nodes
        self.nodes = mem_.nodes

        import mem_.util
        self.util = mem_.util

        import mem_.tasks.gcc
        import mem_.tasks.swig
        import mem_.tasks.ar
        import mem_.tasks.asciidoc
        import mem_.tasks.command
        import mem_.tasks.fs

        self.tasks = mem_.tasks
        self.failed = False

    def concurrency(self, threads):
        if (threads > 0):
            self.thread_limit = threading.Semaphore(threads)

    def import_memfile(self, f):
        """this is mainly for the 'mem' script, don't call directly otherwise"""
        return util.import_module(f, f)


    class subdir(object):
        """
        Import's the Memfile in subdir and return a wrapper that
        allows methods on it to be called.
        """
        def __init__(self, subdir, memfile="Memfile"):
            self.orig_dir = os.path.abspath(os.curdir)
            self.subdir = os.path.join(self.orig_dir, subdir)
            self.memfile = os.path.join(subdir, memfile)
            self.mf = util.import_module(self.memfile, self.memfile)

        def __getattr__(self, memfunc):
            def f(*args, **kwargs):
                os.chdir(self.subdir)
                self.cwd = self.subdir
                if memfunc not in self.mf.__dict__:
                    self.fail("requested method '%s()' doesn't exist in %s" %
                              (memfunc,
                               os.path.join(self.orig_dir, self.memfile)))
                result = self.mf.__dict__[memfunc](*args, **kwargs)
                os.chdir(self.orig_dir)
                self.cwd = self.orig_dir
                return result
            return f


    def fail(self, msg=None):
        if self.failed:
            sys.exit(1)

        print "-" * 50
        if msg:
            sys.stderr.write("build failed: %s\n" % msg)
        else:
            sys.stderr.write("build failed.\n")

        self.failed = True

        # Make sure all possible threads get released
        if not self.thread_limit == None:
            tmp = threading.activeCount()
            for _ in range(tmp):
                self.thread_limit.release()

        sys.exit(1)

    def deps_stack(self):
        try:
            return self.local.deps_stack
        except AttributeError:
            self.local.deps_stack = DepsStack()
            return self.local.deps_stack

    def add_dep(self, d):
        self.deps_stack().add_dep(d)

    def add_deps(self, ds):
        self.deps_stack().add_deps(ds)

    def get_hash(self, *o):
        def gh(objs):
            if isinstance(objs, types.ModuleType):
                return self.nodes.File(objs.__file__).get_hash()
            elif hasattr(objs, "__iter__"):
                if isinstance(objs, dict):
                    return "\1" + "\0".join([gh(k) + "\3" + gh(objs[k])
                                             for k in objs])
                else:
                    return "\1" + "\0".join([gh(obj) for obj in objs]) + "\1"
            else:
                if hasattr(objs, "get_hash"):
                    return objs.get_hash()
                else:
                    return pickle.dumps(objs, 2)
        return sha.new(gh(o)).hexdigest()

    def _deps_path(self, tchash):
        return os.path.join(self.deps_dir, tchash[:2], tchash[2:])

    def _results_path(self, rhash):
        return os.path.join(self.results_dir, rhash[:2], rhash[2:])

    def memoize(self, taskf):
        def f(*args, **kwargs):
            tchash = self.get_hash(taskf.__name__, taskf.__module__,
                                   args, kwargs)
            try:
                f = open(self._deps_path(tchash), "rb")
                deps = pickle.load(f)
                f.close()

                f = open(self._results_path(self.get_hash(tchash, deps)), "rb")
                result = pickle.load(f)
                f.close()

                def restore(o):
                    if (hasattr(o, "restore")):
                        o.restore()
                    elif (hasattr(o, "__iter__")):
                        for el in o:
                            restore(el)

                restore(result)

                return result
            except IOError:
                return self._run_task(taskf, args, kwargs, tchash)

        return f

    def _run_task(self, taskf, args, kwargs, tchash):
        self.deps_stack().call_start()
        result = taskf(*args, **kwargs)
        if self.failed:
            sys.exit(1)

        deps = self.deps_stack().call_finish()

        def store(o):
            if (hasattr(o, "store")):
                o.store()
            elif (hasattr(o, "__iter__")):
                for el in o:
                    store(el)

        store(result)

        fp = self._deps_path(tchash)
        self.util.ensure_file_dir(fp)
        f = open(fp, "wb")
        pickle.dump(deps, f)
        f.close()

        fp = self._results_path(self.get_hash(tchash, deps))
        self.util.ensure_file_dir(fp)
        f = open(fp, "wb")
        pickle.dump(result, f)
        f.close()

        return result

