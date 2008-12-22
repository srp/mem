import cPickle as pickle
import git_repo
import os
import sha
import shelve

MEM_DIR = ".mem"
MEM_GIT_DIR = os.path.join(MEM_DIR, "git-repo")
MEM_DEPS_FILE = os.path.join(MEM_DIR, "deps")
MEM_RESULT_FILE = os.path.join(MEM_DIR, "result")

if not os.path.exists(MEM_DIR):
    os.mkdir(MEM_DIR)
git = git_repo.GitRepo(MEM_GIT_DIR)

taskcall_deps = shelve.open(MEM_DEPS_FILE)
taskcall_result = shelve.open(MEM_RESULT_FILE)

def get_hash(*o):
    def gh(objs):
        if hasattr(objs, "__iter__"):
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

deps_stack = DepsStack()

def task(taskf):
    def f(*args, **kwargs):
        tchash = get_hash(taskf.__name__, taskf.__module__, args, kwargs)

        def run():
            deps_stack.call_start()
            result = taskf(deps_stack, *args, **kwargs)
            deps = deps_stack.call_finish()

            taskcall_deps[tchash] = deps
            taskcall_result[get_hash(tchash, deps)] = result
            if (hasattr(result, "store")):
                result.store()
            return result

        try:
            deps = taskcall_deps[tchash]
            result = taskcall_result[get_hash(tchash, deps)]
            if (hasattr(result, "restore")):
                result.restore()
            return result
        except KeyError:
            return run()

    return f

def with_env(**kwargs):
    def decorator(f):
        def new_f(*args, **fkwargs):
            if fkwargs.has_key("env"):
                fenv = fkwargs.pop("env")
                for k in kwargs.keys():
                    if not fkwargs.has_key(k):
                        if fenv.has_key(k):
                            fkwargs[k] = fenv[k]
                        else:
                            fkwargs[k] = kwargs[k]
            return f(*args, **fkwargs)
        return new_f
    return decorator
