from __future__ import with_statement
import mem
import os

class File(object):
    hash_cache = {}

    def __init__(self, path, filehash=None):
        self.path = os.path.join(mem.cwd, path)
        self.hash = filehash or mem.git.hash_object(path).strip()

    def __repr__(self):
        return "File(path='%s', hash='%s')" % (self.path, self.hash)

    def __str__(self):
        return self.path

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

    def get_hash(self):
        try:
            return File.hash_cache[self.path]
        except KeyError:
            h = mem.git.hash_object(self.path).strip()
            File.hash_cache[self.path] = h
            return h

    def __getstate__(self):
        """return the part of the state to pickle when acting as a result"""
        return {"path": self.path,
                "hash": self.hash}

class Env(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("'Env' objec has no attribute '%s'" % key)

    def __setattr__(self, key, val):
        self[key] = val

    def __repr__(self):
        return "Env(" + " ".join("%s=%s" % (k, repr(v))
                                 for k,v in self.items()) + ")"

    def __str__(self):
        return repr(self)

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
                self[key] == value

    def subst(self, value):
        return value % self

    def get_override(self, key, default=None):
        if default:
            return default
        else:
            return self[key]
