from __future__ import with_statement
import mem
import os

class File(object):
    def __init__(self, path, filehash=None):
        self.path = path
        self.hash = filehash or mem.git.hash_object(path).strip()

    def __repr__(self):
        return "File(path='%s', hash='%s')" % (self.path, self.hash)

    def _is_changed(self):
        return mem.git.hash_object(self.path).strip() != self.hash

    def restore(self):
        if not os.path.exists(self.path):
            self._restore()
        else:
            if self._is_changed():
                self._restore()

    def _restore(self):
        with open(self.path, "wb") as f:
            print "Restoring: " + self.path
            mem.git.cat_file("blob", self.hash, stdout=f)
            return self

    def store(self):
        mem.git.hash_object("-w", self.path)

    def hash(self):
        return mem.git.hash_object(self.path).strip()


class Env(object):
    class EnvDep(object):
        def __init__(self, env, key):
            self.env = env
            self.key = key

        def hash(self):
            return self.env[self.key]

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

    def __setattr__(self, key, val):
        self.__dict__[key] = val

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key):
        self.__dict__[key] = val

    def __repr__(self):
        return "Env(" + \
            " ".join("%s='%s'" % (k,v) for k,v in self.d.items()) + ")"

    def __str__(self):
        return repr(self)

    def get(self, m, key):
        m.add_dep(self.dep(key))
        return self.d[key]

    def dep(self, key):
        return EnvDep(key)

    def deps(self, keys):
        return [EnvDep(key) for key in keys]

