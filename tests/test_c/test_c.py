#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import shutil

sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))

from nose.tools import *
from nose.plugins.attrib import attr

from mem.tasks.gcc import *
from util import FunctionalTest, FileHash
import mem

class CBuildsBase(FunctionalTest):
    root = os.path.dirname(__file__)

class TestObjBuilding_Simple(CBuildsBase):
    created_files = [ 'hello.o' ]
    @attr("slow", "functional")
    def test(self):
        def build():
            obj("hello.c")

        mem.do_build(self.root, build)

        self.assert_all_files_exist()

class TestObjBuilding_Simple(CBuildsBase):
    created_files = [ 'hello.o' ]
    @attr("slow", "functional")
    def test(self):
        def build():
            obj("hello.c")

        mem.do_build(self.root, build)

        self.assert_all_files_exist()


class TestObjBuilding_TwoSimples(CBuildsBase):
    created_files = [ 'hello.o', 'main.o' ]
    @attr("slow", "functional")
    def test(self):
        def build():
            obj(["hello.c", 'main.c'])

        mem.do_build(self.root, build)

        self.assert_all_files_exist()

class TestProgBuilding_Simple(CBuildsBase):
    created_files = [ 'hello', 'hello.o', 'main.o' ]
    @attr("slow", "functional")
    def test(self):
        def build():
            prog("hello", objs = [obj(["main.c", "hello.c"])])

        mem.do_build(self.root, build)

        self.assert_all_files_exist()

