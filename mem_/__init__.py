import cPickle as pickle
import git_repo
import imp
import os
import sha
import shelve
import sys
import types

import util

import threading

MEM_DIR = ".mem"
GIT_DIR = "git-repo"
DEPS_FILE = "deps"
RESULT_FILE = "result"

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

        self.git = git_repo.GitRepo(os.path.join(memdir, GIT_DIR))
        self.taskcall_deps = shelve.open(os.path.join(memdir, DEPS_FILE))
        self.taskcall_result = shelve.open(os.path.join(memdir, RESULT_FILE))

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

    def __shutdown__(self):
        self.taskcall_deps.close()
        self.taskcall_result.close()

    def import_memfile(self, f):
        return util.import_module(f, f)

    def build(self, subdir, *args, **kwargs):
        memfunc = "build"
        if kwargs.has_key("MEM_FUNC"):
            memfunc = kwargs.pop("MEM_FUNC")
        mf = self.import_memfile(os.path.join(subdir, "Memfile"))
        d = os.path.abspath(os.curdir)
        subdir = os.path.join(d, subdir)
        os.chdir(subdir)
        self.cwd = subdir
        func = mf.__dict__[memfunc]
        result = apply(func, args, kwargs)
        os.chdir(d)
        self.cwd = d
        return result

    def fail(self, msg=None):
        print "-" * 50
        if msg:
            sys.stderr.write("build failed: %s\n" % msg)
        else:
            sys.stderr.write("build failed.\n")

        self.taskcall_deps.close()
        self.taskcall_result.close()

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

    def memoize(self, taskf):
        def f(*args, **kwargs):
            tchash = self.get_hash(taskf.__name__, taskf.__module__,
                                   args, kwargs)

            def run():
                self.deps_stack().call_start()
                result = taskf(*args, **kwargs)
                deps = self.deps_stack().call_finish()

                self.taskcall_deps[tchash] = deps
                self.taskcall_result[self.get_hash(tchash, deps)] = result

                def store(o):
                    if (hasattr(o, "store")):
                        o.store()
                    elif (hasattr(o, "__iter__")):
                        for el in o:
                            store(el)

                store(result)

                return result

            try:
                deps = self.taskcall_deps[tchash]
                result = self.taskcall_result[self.get_hash(tchash, deps)]

                def restore(o):
                    if (hasattr(o, "restore")):
                        o.restore()
                    elif (hasattr(o, "__iter__")):
                        for el in o:
                            restore(el)

                restore(result)

                return result
            except KeyError:
                return run()

        return f
