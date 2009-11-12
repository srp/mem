#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import shutil

sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))

from nose.tools import *
from nose.plugins.attrib import attr

from mem.tasks.pdflatex import pdflatex
from util import FunctionalTest, FileHash
import mem

class PDFLatexBuildsBase(FunctionalTest):
    root = os.path.dirname(__file__)

class TestPDFLatexBuilds_Simple(PDFLatexBuildsBase):
    created_files = [ 'simple.aux', 'simple.pdf', 'simple.log' ]
    @attr("slow", "functional")
    def test(self):
        def build():
            pdflatex("simple.tex")

        mem.do_build(self.root, build)

        self.assert_all_files_exist()

class TestPDFLatexBuilds_BuildAndRestore(PDFLatexBuildsBase):
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

class TestPDFLatexBuilds_BuildChangeAndRebuild(PDFLatexBuildsBase):
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

class TestPDFLatexBuilds_BuildChangeIncludedAndRebuild(PDFLatexBuildsBase):
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








