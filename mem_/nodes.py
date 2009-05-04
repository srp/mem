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
import hashlib
import os
import cPickle as pickle
import types
import shutil
import sys

import exceptions
class NodeError(exceptions.Exception):
    def __init__(self, message):
        self.msg = message

    def __str__(self):
        return self.msg


class File(str):
    _hash_cache = {}

    def __new__(self, file, *args, **kwargs):
	import mem
        path = os.path.join(mem.cwd, file)
	if mem.failed:
		sys.exit(1)
        if not os.path.exists(path):
            raise NodeError("%s does not exist!" % path)
        return str.__new__(self, path)

    def __init__(self, file, filehash=None):
        self._hash = filehash or self.get_hash()

    def __repr__(self):
        return "File('%s', hash='%s')" % (self, self._hash)

    #
    # user convience functions
    #
    def basename(self):
        return os.path.basename(self)

    def dirname(self):
        return os.path.dirname(self)

    def exists(self):
        return os.path.exists(self)

    def splitext(self):
        return os.path.splitext(self)

    def stat(self):
        return os.stat(self)

    def unlink(self):
        return os.unlink(self)

    #
    # methods for acting as a node
    #

    def _is_changed(self):
        return self.get_hash() != self._hash

    def _store_path(self):
        h = self._hash
        return os.path.join(mem.blob_dir, h[:2], h[2:])

    def restore(self):
        if not self.exists():
            self._restore()
        elif self._is_changed():
            self._restore()

    def _restore(self):
        if not os.path.exists(self.dirname()):
	    os.makedirs(self.dirname())
        if self.exists():
            self.unlink()
        with open(self, "wb") as f:
            print "Restoring:", self
            shutil.copy2(self._store_path(), self)
            return self

    def store(self):
        spath = self._store_path()
        mem.util.ensure_file_dir(spath)
        if os.path.exists(self._store_path()):
            return
        shutil.copy2(self, spath)

    def get_hash(self):
        try:
            return File._hash_cache[self]
        except KeyError:
            h = self._compute_hash()
            File._hash_cache[self] = h
            return h

    def _compute_hash(self):
        if not self.exists():
            # if the file doesn't exist, hash to something unique
            # so that cache lookup will fail
            return "NOT FOUND"
	f = open(self, "rb")
        s = hashlib.sha1()
        st = self.stat()
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
        return {"path": self,
                "hash": self._hash}

    def __setstate__(self, d):
        """return the part of the state to pickle when acting as a result"""
        str.__init__(self, d["path"])
        self._hash = d["hash"]
