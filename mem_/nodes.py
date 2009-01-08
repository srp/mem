from __future__ import with_statement
import mem
import os
import cPickle as pickle
import types
import sys

import exceptions
class NodeError(exceptions.Exception):
	def __init__(self, message):
            self.message = message

	def __str__(self):
            return self.message




class File(object):
    hash_cache = {}

    def __init__(self, path, filehash=None):
	import mem
        self.path = os.path.join(mem.cwd, path)
	if mem.failed:
		sys.exit(1)
        if not os.path.exists(path):
            raise NodeError("%s does not exist!" % path)

        self.hash = filehash or self.get_hash()

    def __repr__(self):
        return "File(path='%s', hash='%s')" % (self.path, self.hash)

    def __str__(self):
        return self.path

    def _is_changed(self):
        return self.get_hash() != self.hash

    def restore(self):
        if not os.path.exists(self.path):
            self._restore()
        elif self._is_changed():
            self._restore()

    def _restore(self):
        if not os.path.exists(os.path.dirname(self.path)):
	    os.makedirs(os.path.dirname(self.path))
        if os.path.exists(self.path):
            os.unlink(self.path)
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

    def get_override(self, key, default=None):
        if default:
            return default
        else:
            return self[key]
