#!/usr/bin/env python

from __future__ import with_statement

import os
import git_repo
import cPickle as pickle
import sha
import shelve
import subprocess

MEM_DIR = ".mem"
MEM_GIT_DIR = os.path.join(MEM_DIR, "git-repo")
MEM_DEPS_FILE = os.path.join(MEM_DIR, "deps")
MEM_RESULT_FILE = os.path.join(MEM_DIR, "result")

if not os.path.exists(MEM_DIR):
    os.mkdir(MEM_DIR)
git = git_repo.GitRepo(MEM_GIT_DIR)

taskcall_deps = shelve.open(MEM_DEPS_FILE)
taskcall_result = shelve.open(MEM_RESULT_FILE)

def mem_pickle(objs):
    if hasattr(objs, "__iter__"):
        return "\1" + "\0".join(mem_pickle(obj) for obj in objs) + "\1"
    else:
        if hasattr(objs, "mem_pickle"):
            return objs.mem_pickle()
        else:
            return pickle.dumps(objs, 2)

def sha1(*o):
    return sha.new(mem_pickle(o)).hexdigest()


class Dependency(object):
    pass

class File(object):
    def __init__(self, path):
        self.path = path
        self.hash = git.hash_object(path).strip()

    def __repr__(self):
        return "<File path='%s' hash='%s'>" % (self.path, self.hash)

    def _is_changed(self):
        return git.hash_object(self.path).strip() != self.hash

    def restore(self):
        if not os.path.exists(self.path):
            self._restore()
        else:
            if self._is_changed():
                self._restore()

    def _restore(self):
        with open(self.path, "wb") as f:
            print "Restoring: " + self.path
            git.cat_file("blob", self.hash, stdout=f)
            return self

    def store(self):
        git.hash_object("-w", self.path)

    def mem_pickle(self):
        return git.hash_object(self.path).strip()

class DepsStack(object):
    def __init__(self):
        self.deps = []

    def call_start(self):
        self.deps.append([])

    def call_finish(self):
        return self.deps.pop()

    def register(self, deps):
        self.deps[-1].extend(deps)

deps_stack = DepsStack()

def register_dep(dep):
    deps_stack.register([dep])

def register_deps(deps):
    deps_stack.register(deps)

def task(taskf):
    def f(*args, **kwargs):
        tchash = sha1(taskf.__name__, taskf.__module__, args, kwargs)

        def run():
            deps_stack.call_start()
            result = taskf(*args, **kwargs)
            deps = deps_stack.call_finish()

            taskcall_deps[tchash] = deps
            taskcall_result[sha1(tchash, deps)] = result
            if (hasattr(result, "store")):
                result.store()
            return result

        try:
            deps = taskcall_deps[tchash]
            result = taskcall_result[sha1(tchash, deps)]
            if (hasattr(result, "restore")):
                result.restore()
            return result
        except KeyError:
            return run()

    return f

@task
def make_depends(source):
    return popen(["gcc", "-M", "-o", "-", File(source)]).readlines()

@task
def obj(target, source):
    args = ["gcc", "-c", "-o", target, source]
    print " ".join(args)
    assert subprocess.call(args) == 0
    register_dep(File(source))
    return File(target)

@task
def prog(target, *objs):
    args = ["gcc", "-o", target] + [o.path for o in objs]
    print " ".join(args)
    assert subprocess.call(args) == 0
    register_deps(objs)
    return File(target)


taskcall_deps.close()
taskcall_result.close()

