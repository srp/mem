#!/usr/bin/env python
# encoding: utf-8

import os
import shutil
from hashlib import sha1

from nose.tools import *

import mem

class FunctionalTest(object):
    to_be_deleted = []
    root = os.path.dirname(__file__)

    def setup(self):
        self._cwd = os.getcwd()
        os.chdir(self.root)

    def teardown(self):
        self._delete_files()

        os.chdir(self._cwd)

        mem.Mem.destroy()

    def _delete_files(self):
        for f in self.created_files + self.to_be_deleted + [ '.mem' ]:
            if not os.path.exists(f):
                continue

            if os.path.isdir(f):
                shutil.rmtree(f)
            else:
                os.unlink(f)

    def assert_all_files_exist(self):
        for f in self.created_files:
            ok_(os.path.exists(f), "File '%s' doesn't exist!" % f)

class FileHash(object):
    """
    This class calculates a sha1 hash from a given file and can be asked
    periodically, if the file has changed
    """
    def __init__(self, filename):
        self._file = filename
        self._hash = self._calc_hash()

    @property
    def changed(self):
        h = self._calc_hash()
        return h != self._hash

    def _calc_hash(self):
        return sha1(open(self._file,"rb").read()).hexdigest()


