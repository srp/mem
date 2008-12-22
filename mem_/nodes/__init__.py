from __future__ import with_statement
import mem
import os

class File(object):
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
        # TODO: this gets repeated similar calls, cache them
        return mem.git.hash_object(self.path).strip()

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
        ndict = {}
        ndict.update(self)
        for key in kwargs:
            value = kwargs[key]
            if type(value) == str:
                ndict[key] = value % ndict
            elif type(value) == list:
                nlist = []
                for el in value:
                    if type(el) == str:
                        nlist.append(el % ndict)
                    else:
                        nlist.append(el)
                ndict[key] = nlist
            else:
                ndict[key] == value

        self.update(ndict)

    def subst(self, value):
        return value % self.__dict__["d"]

    def get(self, key, default=None):
        return self.__dict__["d"].get(key, default)


    def has_key(self, key):
        return self.__dict__["d"].has_key(key)

    def dep(self, key):
        return self.EnvDep(self, key)

    def deps(self, keys):
        return [self.EnvDep(self, key) for key in keys]
