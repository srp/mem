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

def make_depends(target, source, CFLAGS, CPPPATH):
    includes = ["-I" + path for path in CPPPATH]
    args = mem.util.convert_cmd(["gcc"] + CFLAGS +
                                ["-I" +
                                 os.path.dirname(target)] +
                                includes + ["-M", "-o", "-", source])
    print " ".join(args)
    p = subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
    deps = p.stdout.read().split()
    if p.wait() != 0:
        mem.fail()

    deps = deps[1:] # first element is the target (eg ".o"), drop it
    return [dep for dep in deps if dep != '\\']

@mem.util.with_env(CFLAGS=[], CPPPATH=[])
@mem.memoize
def t_c_obj(target, source, CFLAGS, CPPPATH):
    if not os.path.exists(str(source)):
        mem.fail("%s does not exist" % source)

    mem.add_dep(mem.util.convert_to_file(source))
    mem.add_deps([File(f) for f in
                  make_depends(target, source, CFLAGS=CFLAGS, CPPPATH=CPPPATH)])
    includes = ["-I" + path for path in CPPPATH]
    args = mem.util.convert_cmd(["gcc"] +  CFLAGS + includes +
                                ["-I" +
                                 os.path.dirname(target)] +
                                ["-c", "-o", target, source])
    print " ".join(args)

    mem.util.ensure_file_dir(target)
    if subprocess.call(args) != 0:
        mem.fail()
    return File(target)

@mem.util.with_env(CXXFLAGS=[], CPPPATH=[])
@mem.memoize
def t_cpp_obj(target, source, CXXFLAGS, CPPPATH):
    if not os.path.exists(str(source)):
        mem.fail("%s does not exist" % source)

    mem.add_dep(mem.util.convert_to_file(source))
    mem.add_deps([File(f) for f in
                  make_depends(target, source,
                               CFLAGS=CXXFLAGS, CPPPATH=CPPPATH)])
    includes = ["-I" + path for path in CPPPATH]
    args = mem.util.convert_cmd(["g++"] +  CXXFLAGS + includes +
                                ["-I" +
                                 os.path.dirname(target)] +
                                ["-c", "-o", target, source])
    print " ".join(args)

    mem.util.ensure_file_dir(target)
    if subprocess.call(args) != 0:
        mem.fail()
    return File(target)

@mem.util.with_env(CFLAGS=[], LIBS=[], LIBPATH=[])
@mem.memoize
def t_prog(target, objs, CFLAGS, LIBS, LIBPATH):
    mem.add_deps(objs)

    npaths = map(lambda a: "-L" + str(a), LIBPATH)
    nlibs = map(lambda a: "-l" + str(a), LIBS)

    args = mem.util.convert_cmd(["gcc", "-o", target] + CFLAGS +
                                npaths + nlibs + [o.path for o in objs])

    print " ".join(args)

    mem.util.ensure_file_dir(target)
    if subprocess.call(args) != 0:
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
        if target:
            source = os.path.join(os.getcwd(), source_list)
            (name, ext) = os.path.splitext(str(source))
            if name.startswith(os.getcwd()):
                name = name[:len(os.getcwd()) + 1]
            t = os.path.join(BuildDir, str(target))
            thread = build_obj(t, source, ext, env, **kwargs)
            thread.join()
            return [thread.result]
        else:
            source_list = [source_list]

    if target:
        mem.fail("Cannot specify target on a list of objects")

    nslist = mem.util.flatten(source_list)
    for source in nslist:
        (name, ext) = os.path.splitext(str(source))
        target = os.path.join(BuildDir,  name + ".o")

        source = os.path.join(os.getcwd(), str(source))
        if not ext == ".h":
            threads.append(build_obj(target, source, ext, env, **kwargs))

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
