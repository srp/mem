from __future__ import with_statement
import mem
import os
import cPickle as pickle
import types

import exceptions
class NodeError(exceptions.Exception):
	def __init__(self, message):
            self.message = message

	def __str__(self):
            return self.message




class File(object):
    hash_cache = {}

    def __init__(self, path, filehash=None):
        self.path = os.path.join(mem.cwd, path)
        if not os.path.exists(path):
            raise NodeError("%s does not exist!" % path)

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

class DepFiles(object):
    """ A 'batch' of dependencies that a treated as a group. """

    def __init__(self, paths):
        """ This initializer may take one of three things. A string
        reperesenting a file, a mem.nodes.File object or a mem.nodes.DepFiles
        object. It may either take a single object or a list of said objects """
        # pickle doesn't work on generators, so convert to list first
        if (isinstance(paths, types.GeneratorType)):
            paths = list(paths)

        if not isinstance(paths, list):
            paths = [paths]

        self.paths = []
        for path in paths:
            if isinstance(path, str):
                self.paths.append(path)
            elif isinstance(path, DepFiles):
                self.paths.extend(path.paths)
            elif isinstance(path, File):
                self.paths.append(str(path))
            else:
                raise NodeError("unexpected argument in DepFiles %s" % str(path))



    def get_hash(self):
        known = [(p, File.hash_cache[p])
                 for p in self.paths if p in File.hash_cache]
        unknown = [p for p in self.paths if p not in File.hash_cache]
        unknown_hash = mem.git.hash_object("--", *unknown)
        for i in range(len(unknown)):
            File.hash_cache[unknown[i]] = unknown_hash[i]
            known.append((unknown[i], unknown_hash[i]))
        known.sort()
        return pickle.dumps(known)

    def __repr__(self):
        return "DepFiles(paths=%s)" % (self.paths)

    def __str__(self):
        return self.__repr__()


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
