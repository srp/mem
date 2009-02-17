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
    print " ".join(args)
    p = subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
    deps = p.stdout.read().split()
    if p.wait() != 0:
        mem.fail()

    deps = deps[1:] # first element is the target (eg ".c"), drop it
    return [dep for dep in deps if dep != '\\']


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

    wrap = os.path.join(BuildDir, os.path.splitext(source)[0] + "_wrap.c")
    args = mem.util.convert_cmd(['swig', '-o', wrap, '-outdir', tmpdir] +
                                SWIGFLAGS + [source])
    print " ".join(args)

    p = subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
    if p.wait() != 0:
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

    env = env.copy()
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
        jtargets.extend(env.java(jtargets, env=env,
                                 JAVA_FLAGS=env.get("SWIG_JAVA_FLAGS", [])))

    return mem.util.convert_to_files(ctargets + ntargets + jtargets)
