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

import os.path
import re
import subprocess
from subprocess import PIPE
import tempfile
import shutil
import mem

# Match '%module test', as well as '%module(directors="1") test'
re_module = re.compile(r'%module(?:\s*\(.*\))?\s+(.+)')

def make_depends(source, SWIGFLAGS):
    args = mem.util.convert_cmd(["swig"] + SWIGFLAGS +
                                ["-M", source])
    return mem.util.make_depends("SWIG depends", source, args)

@mem.util.with_env(SWIGFLAGS=[])
@mem.memoize
def generate(BuildDir, source, SWIGFLAGS):
    mem.add_dep(mem.util.convert_to_file(source))
    mem.add_deps([mem.nodes.File(f) for f in make_depends(source, SWIGFLAGS)])

    # since we have no way to know all the files that swig will generate,
    # we have it generate into a temp directory, then we can see what
    # exact files were produced, and move them to their proper location.
    mem.util.ensure_file_dir(BuildDir)
    tmpdir = tempfile.mkdtemp(dir=BuildDir)

    if "-c++" in SWIGFLAGS:
        wrap_ext = ".cpp"
    else:
        wrap_ext = ".c"

    wrap = os.path.join(BuildDir, os.path.splitext(source)[0] + "_wrap" + wrap_ext)
    args = mem.util.convert_cmd(['swig', '-o', wrap, '-outdir', tmpdir] +
                                SWIGFLAGS + [source])

    if mem.util.run("SWIG", source, args) != 0:
        mem.fail()

    files = os.listdir(tmpdir)
    for file in files:
        shutil.move(os.path.join(tmpdir, file), os.path.join(BuildDir, file))

    os.rmdir(tmpdir)

    return [mem.nodes.File(os.path.join(BuildDir, file)) for file in files] + \
        [mem.nodes.File(wrap)]


def obj(sources, env=None, build_dir=None, **kwargs):
    if not type(sources) == list:
        sources = [sources]

    env = env.shallow_copy()
    env.update(kwargs)

    sources = mem.util.flatten(sources)
    BuildDir = mem.util.get_build_dir(env, build_dir)

    targets = []
    threads = []
    for source in sources:
        (name, ignore) = os.path.splitext(str(source))
        t = mem.util.Runable(generate, BuildDir, source, env=env)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
        targets.extend(t.result)

    ntargets = []
    ctargets = []
    jtargets = []
    for target in mem.util.flatten(targets):
        if str(target).endswith(".c"):
            ctargets.append(target)
        elif str(target).endswith(".java"):
            jtargets.append(target)
        else:
            ntargets.append(target)

    ctargets.extend(env.c.obj(ctargets, env=env,
                              CFLAGS=env.get("SWIG_CFLAGS", [])))
    if jtargets:
        jtargets.extend(
            env.java.compile(jtargets,
                             JAVA_FLAGS=env.get("SWIG_JAVA_FLAGS", []),
                             env=env))

    return mem.util.convert_to_files(ctargets + ntargets + jtargets)

def only_object_files(lst):
	return [a for a in lst if a.endswith(".o")]

def shared_obj(shared_obj, sources, env=None, build_dir=None, **kwargs):
    deps = obj(sources, env, build_dir, **kwargs)
    objs = only_object_files(deps)
    gcc_kwargs = kwargs.copy()
    if 'SWIGFLAGS' in gcc_kwargs:
        del gcc_kwargs['SWIGFLAGS']
    if 'SWIG_CFLAGS' in gcc_kwargs:
        del gcc_kwargs['SWIG_CFLAGS']

    additional_objs = gcc_kwargs.pop('additional_objs', [])

    so = env.c.shared_obj(shared_obj, objs + additional_objs, env, build_dir,
                          CFLAGS=env.SWIG_CFLAGS, **gcc_kwargs)
    return [so] + objs
