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

import os
import subprocess
from subprocess import PIPE
import sys
from threading import Thread

import mem
from mem._mem import Mem
from mem import nodes
from mem import util

def target_inc_flag(target, source_list):
    inc_target = False
    for source in source_list:
        if os.path.dirname(target) != os.path.dirname(source):
            inc_target = True

    if inc_target:
        return ["-I" + os.path.dirname(target)]
    return []

def make_depends(target, source_list, CC, CFLAGS, CPPPATH, inc_dirs):
    includes = ["-I" + path for path in CPPPATH]
    deps = []
    for s in source_list:
        deps += make_depends_single(target, s,
                                    CC, CFLAGS, includes,
                                    target_inc_flag(target, source_list),
                                    inc_dirs)
    return deps

def make_depends_single(target, source,
                        CC, CFLAGS, includes, target_inc, inc_dirs):
    mem.add_dep(util.convert_to_file(source))
    args = util.convert_cmd([CC] + CFLAGS +
                                includes +
                                target_inc +
                                inc_dirs +
                                ["-M", "-o", "-", source])
    return util.make_depends("GCC depends", source, args)

@util.with_env(CC="gcc", CFLAGS=[], CPPPATH=[])
@mem.memoize
def t_c_obj(target, source_list, CC, CFLAGS, CPPPATH):
    inc_dirs = set()
    if len(source_list) > 1:
        combine_opt=['-combine']
    else:
        combine_opt=[]

    for source in source_list:
        inc_dirs.add("-I" + os.path.dirname(source))
        if not os.path.exists(str(source)):
            Mem.instance().fail("%s does not exist" % source)

        mem.add_dep(util.convert_to_file(source))

    mem.add_deps([nodes.File(f) for f in
                  make_depends(target, source_list,
                               CC=CC, CFLAGS=CFLAGS, CPPPATH=CPPPATH,
                               inc_dirs=list(inc_dirs))])
    includes = ["-I" + path for path in CPPPATH]
    args = util.convert_cmd([CC] +  CFLAGS + includes +
                                target_inc_flag(target, source_list) +
                                list(inc_dirs) +
                                combine_opt +
                                ["-c", "-o", target] + source_list)
    util.ensure_file_dir(target)

    if util.run("GCC", source_list, args) != 0:
        Mem.instance().fail()

    return nodes.File(target)

@util.with_env(CXXFLAGS=[], CPPPATH=[])
@mem.memoize
def t_cpp_obj(target, source_list, CXXFLAGS, CPPPATH):
    inc_dirs = set()
    if len(source_list) > 1:
        combine_opt=['-combine']
    else:
        combine_opt=[]

    for source in source_list:
        inc_dirs.add("-I" + os.path.dirname(source))
        if not os.path.exists(str(source)):
            Mem.instance().fail("%s does not exist" % source)

            mem.add_dep(util.convert_to_file(source))

    mem.add_deps([nodes.File(f) for f in
                  make_depends(target, source_list,
                               CFLAGS=CXXFLAGS, CPPPATH=CPPPATH,
                               inc_dirs = list(inc_dirs))])

    includes = ["-I" + path for path in CPPPATH]
    args = util.convert_cmd(["g++"] +  CXXFLAGS + includes +
                                target_inc_flag(target, source_list) +
                                list(inc_dirs) +
                                combine_opt +
                                ["-c", "-o", target] + source_list)

    util.ensure_file_dir(target)

    if util.run("Compiling", source_list, args) != 0:
        Mem.instance().fail()

    return nodes.File(target)

@util.with_env(CC="gcc", CFLAGS=[], LIBS=[], LIBPATH=[], LINKFLAGS=[])
@mem.memoize
def t_prog(target, objs, CC, CFLAGS, LIBS, LIBPATH, LINKFLAGS):
    mem.add_deps(objs)

    npaths = map(lambda a: "-L" + str(a), LIBPATH)
    nlibs = map(lambda a: "-l" + str(a), LIBS)

    args = util.convert_cmd([CC, "-o", target] + CFLAGS + LINKFLAGS +
                                npaths + objs + nlibs)

    util.ensure_file_dir(target)

    if util.run("Linking", target, args) != 0:
        Mem.instance().fail()

    return nodes.File(target)


def build_obj(target, source, ext, env=None, **kwargs):
    if ext == ".c":
        t = util.Runable(t_c_obj, target, source, env=env, **kwargs)
        t.start()
        return t

    elif ext == ".cpp":
        t = util.Runable(t_cpp_obj, target, source, env=env, **kwargs)
        t.start()
        return t
    else:
        Mem.instance().fail("Don't know how to build %s" % source)

    return t


def obj(source_list, target=None, env=None, build_dir=None, **kwargs):
    """ Take a list of sources and convert them to a correct object file """

    BuildDir = util.get_build_dir(env, build_dir)
    threads = []

    if not type(source_list) == list:
            source_list = [source_list]

    nslist = util.flatten(source_list)

    # If a target is specified, build all the sources in the list into
    # a single target
    if target:
        buildext = None
        new_source_list = []
        for source in nslist:
            source = os.path.join(os.getcwd(), source)
            (name, ext) = os.path.splitext(str(source))
            if buildext == None:
                buildext = ext
            elif buildext != ext:
                Mem.instance().fail("Mixed extensions in a single build object")
            new_source_list.append(source)

        t = os.path.join(BuildDir, str(target))
        thread = build_obj(t, new_source_list, buildext, env, **kwargs)
        thread.join()
        return [thread.result]

    # No target specified.  Build each object individually
    for source in nslist:
        (name, ext) = os.path.splitext(os.path.basename(str(source)))
        target = os.path.join(BuildDir,  name + ".o")

        source = os.path.join(os.getcwd(), str(source))
        if not ext == ".h":
            threads.append(build_obj(target, [source], ext, env, **kwargs))

    for t in threads:
        if t:
            t.join()

    return [t.result for t in threads if t]

def prog(target, objs, env=None, build_dir = None, **kwargs):
    """ Convert the list of objects into a program given the cflags """
    nobjs = util.flatten(objs)
    BuildDir = util.get_build_dir(env, build_dir)
    ntarget = os.path.join(BuildDir, target)
    t_prog(ntarget, nobjs, env=env, **kwargs)
    return nodes.File(ntarget)

def shared_obj(target, objs, env=None, build_dir = None, **kwargs):
    """ Convert the list of objects into a program given the cflags """
    nobjs = util.flatten(objs)
    BuildDir = util.get_build_dir(env, build_dir)
    ntarget = os.path.join(BuildDir, target)

    if 'CFLAGS' in kwargs:
        merged_CFLAGS = kwargs['CFLAGS'][:]
        del kwargs['CFLAGS']
    else:
        merged_CFLAGS = env.CFLAGS[:]

    merged_CFLAGS.insert(0, "-shared")

    t_prog(ntarget, nobjs, env=env, CFLAGS=merged_CFLAGS, **kwargs)

    return nodes.File(ntarget)
