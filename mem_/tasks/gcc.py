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

File = mem.nodes.File

def target_inc_flag(target, source_list):
    inc_target = False
    for source in source_list:
        if os.path.dirname(target) != os.path.dirname(source):
            inc_target = True

    if inc_target:
        return ["-I" + os.path.dirname(target)]
    return []

def make_depends(target, source_list, CFLAGS, CPPPATH, inc_dirs):
    includes = ["-I" + path for path in CPPPATH]

    deps = []
    for s in source_list:
        args = mem.util.convert_cmd(["gcc"] + CFLAGS +
                                    includes +
                                    target_inc_flag(target, source_list) +
                                    inc_dirs +
                                    ["-M", "-o", "-", s])
        deps += mem.util.make_depends("GCC depends", s, args)
    return deps

@mem.util.with_env(CFLAGS=[], CPPPATH=[])
@mem.memoize
def t_c_obj(target, source_list, CFLAGS, CPPPATH):
    inc_dirs = set()
    if len(source_list) > 1:
        combine_opt=['-combine']
    else:
        combine_opt=[]

    for source in source_list:
        inc_dirs.add("-I" + os.path.dirname(source))
        if not os.path.exists(str(source)):
            mem.fail("%s does not exist" % source)

        mem.add_dep(mem.util.convert_to_file(source))

    mem.add_deps([File(f) for f in
                  make_depends(target, source_list,
                               CFLAGS=CFLAGS, CPPPATH=CPPPATH,
                               inc_dirs=list(inc_dirs))])
    includes = ["-I" + path for path in CPPPATH]
    args = mem.util.convert_cmd(["gcc"] +  CFLAGS + includes +
                                target_inc_flag(target, source_list) +
                                list(inc_dirs) +
                                combine_opt +
                                ["-c", "-o", target] + source_list)
    mem.util.ensure_file_dir(target)

    if mem.util.run("GCC", source_list, args) != 0:
        mem.fail()

    return File(target)

@mem.util.with_env(CXXFLAGS=[], CPPPATH=[])
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
            mem.fail("%s does not exist" % source)

            mem.add_dep(mem.util.convert_to_file(source))

    mem.add_deps([File(f) for f in
                  make_depends(target, source_list,
                               CFLAGS=CXXFLAGS, CPPPATH=CPPPATH,
                               inc_dirs = list(inc_dirs))])

    includes = ["-I" + path for path in CPPPATH]
    args = mem.util.convert_cmd(["g++"] +  CXXFLAGS + includes +
                                target_inc_flag(target, source_list) +
                                list(inc_dirs) +
                                combine_opt +
                                ["-c", "-o", target] + source_list)

    mem.util.ensure_file_dir(target)

    if mem.util.run("Compiling", source_list, args) != 0:
        mem.fail()

    return File(target)

@mem.util.with_env(CFLAGS=[], LIBS=[], LIBPATH=[], LINKFLAGS=[])
@mem.memoize
def t_prog(target, objs, CFLAGS, LIBS, LIBPATH, LINKFLAGS):
    mem.add_deps(objs)

    npaths = map(lambda a: "-L" + str(a), LIBPATH)
    nlibs = map(lambda a: "-l" + str(a), LIBS)

    args = mem.util.convert_cmd(["gcc", "-o", target] + CFLAGS + LINKFLAGS +
                                npaths + objs + nlibs)

    mem.util.ensure_file_dir(target)

    if mem.util.run("Linking", target, args) != 0:
        mem.fail()

    return File(target)


def build_obj(target, source, ext, env=None, **kwargs):
    if ext == ".c":
        t = mem.util.Runable(t_c_obj, target, source, env=env, **kwargs)
        t.start()
        return t

    elif ext == ".cpp":
        t = mem.util.Runable(t_cpp_obj, target, source, env=env, **kwargs)
        t.start()
        return t
    else:
        mem.fail("Don't know how to build %s" % source)

    return t


def obj(source_list, target=None, env=None, build_dir=None, **kwargs):
    """ Take a list of sources and convert them to a correct object file """

    BuildDir = mem.util.get_build_dir(env, build_dir)
    threads = []

    if not type(source_list) == list:
            source_list = [source_list]

    nslist = mem.util.flatten(source_list)

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
                mem.fail("Mixed extensions in a single build object")
            new_source_list.append(source)

        t = os.path.join(BuildDir, str(target))
        thread = build_obj(t, new_source_list, buildext, env, **kwargs)
        thread.join()
        return [thread.result]

    # No target specified.  Build each object individually
    for source in nslist:
        (name, ext) = os.path.splitext(str(source))
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
    nobjs = mem.util.flatten(objs)
    BuildDir = mem.util.get_build_dir(env, build_dir)
    ntarget = os.path.join(BuildDir, target)
    t_prog(ntarget, nobjs, env=env, **kwargs)
    return File(ntarget)

def shared_obj(target, objs, env=None, build_dir = None, **kwargs):
    """ Convert the list of objects into a program given the cflags """
    nobjs = mem.util.flatten(objs)
    BuildDir = mem.util.get_build_dir(env, build_dir)
    ntarget = os.path.join(BuildDir, target)

    if 'CFLAGS' in kwargs:
        merged_CFLAGS = kwargs['CFLAGS'][:]
        del kwargs['CFLAGS']
    else:
        merged_CFLAGS = env.CFLAGS[:]

    merged_CFLAGS.insert(0, "-shared")

    t_prog(ntarget, nobjs, env=env, CFLAGS=merged_CFLAGS, **kwargs)

    return File(ntarget)
