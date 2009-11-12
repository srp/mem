#!/usr/bin/env python
# encoding: utf-8

import os
import shutil
from hashlib import sha1

from nose.tools import *
from nose.plugins.attrib import attr

import mem
from mem.tasks.pdflatex import pdflatex

class FunctionalTest(object):
    to_be_deleted = []
    def setup(self):
        self._cwd = os.getcwd()
        self.root = os.path.dirname(__file__)

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

class TestPDFLatexBuilds_Simple(FunctionalTest):
    created_files = [ 'simple.aux', 'simple.pdf', 'simple.log' ]
    @attr("slow", "functional")
    def test(self):
        def build():
            pdflatex("simple.tex")

        mem.do_build(self.root, build)

        self.assert_all_files_exist()

class TestPDFLatexBuilds_BuildAndRestore(FunctionalTest):
    created_files = [ 'simple.aux', 'simple.pdf', 'simple.log' ]
    @attr("slow", "functional")
    def test(self):
        def build():
            pdflatex("simple.tex")

        mem.do_build(self.root, build)
        mem.Mem.destroy()

        self.assert_all_files_exist()
        h = FileHash("simple.pdf")
        os.unlink("simple.pdf")

        # TODO: ensure here that the file is restored and not rebuild
        # Currently, I have no idea how this could be done
        mem.do_build(self.root, build)
        self.assert_all_files_exist()

        ok_(not h.changed)

class TestPDFLatexBuilds_BuildChangeAndRebuild(FunctionalTest):
    created_files = [ 'simple_c.aux', 'simple_c.pdf', 'simple_c.log' ]
    to_be_deleted = [ "simple_c.tex" ]

    @attr("slow", "functional")
    def test(self):
        def build():
            pdflatex("simple_c.tex")

        shutil.copy("simple.tex", "simple_c.tex")

        mem.do_build(self.root, build)
        mem.Mem.destroy()

        self.assert_all_files_exist()
        h = FileHash("simple_c.pdf")

        shutil.copy("simple1.tex", "simple_c.tex")

        # TODO: ensure the file is rebuild, not restored
        mem.do_build(self.root, build)
        self.assert_all_files_exist()

        ok_(h.changed)

class TestPDFLatexBuilds_BuildChangeIncludedAndRebuild(FunctionalTest):
    created_files = [ 'includer.aux', 'includer.pdf', 'includer.log' ]
    to_be_deleted = [ 'included.tex' ]

    @attr("slow", "functional")
    def test(self):
        def build():
            pdflatex("includer.tex")

        shutil.copy("included1.tex", "included.tex")

        mem.do_build(self.root, build)
        mem.Mem.destroy()

        self.assert_all_files_exist()

        h = FileHash("includer.pdf")

        shutil.copy("included2.tex", "included.tex")

        # TODO: ensure the file is rebuild, not restored
        mem.do_build(self.root, build)
        self.assert_all_files_exist()

        ok_(h.changed)








