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

from __future__ import with_statement
import mem
import os
import cPickle as pickle
import types
import sha
import shutil
import sys

import exceptions
class NodeError(exceptions.Exception):
    def __init__(self, message):
	self.message = message

    def __str__(self):
	return self.message




class File(object):
    _hash_cache = {}

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

    def _store_path(self):
        h = self.hash
        return os.path.join(mem.blob_dir, h[:2], h[2:])

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
            print "Restoring:", self.path
            shutil.copy2(self._store_path(), self.path)
            return self

    def store(self):
        spath = self._store_path()
        mem.util.ensure_file_dir(spath)
        if os.path.exists(self._store_path()):
            return
        shutil.copy2(self.path, spath)

    def get_hash(self):
        try:
            return File._hash_cache[self.path]
        except KeyError:
            h = self._hash()
            File._hash_cache[self.path] = h
            return h

    def _hash(self):
        if not os.path.exists(self.path):
            # if the file doesn't exist, hash to something unique
            # so that cache lookup will fail
            return "NOT FOUND"
	f = open(self.path, "rb")
        s = sha.sha()
        st = os.stat(self.path)
        s.update("blob %d %d\0" % (st[os.path.stat.ST_SIZE],
                                   st[os.path.stat.ST_MODE]))
        data = f.read(1<<16)
        while data != '':
            s.update(data) # 64k blocks
            data = f.read(1<<16)
        f.close()
        return s.hexdigest()

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
