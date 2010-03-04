#!/usr/bin/env python
# encoding: utf-8

"""
Support for building python extensions
"""

# Sadly, we cannot extend shared_obj in a nice and proper way, since it isn't
# a class. We therefore have to rip a leg out to do something in that order,
# a lot of code duplication is not avoidable :(
from distutils.sysconfig import get_config_var

try:
    import cython
    _has_cython = True
except ImportError:
    _has_cython = False

import re

from mem.tasks.gcc import *
from mem._mem import Mem

@util.with_env(CFLAGS=[], CPPPATH=[])
@mem.memoize
def _build_python_obj(target, source, CFLAGS, CPPPATH):
    includes = ["-I" + path for path in CPPPATH]
    if os.path.dirname(source) != '':
        includes.append("-I" + os.path.dirname(source))
    includes.append("-I" + get_config_var("CONFINCLUDEPY"))

    # Check for header dependencies
    mem = Mem.instance()
    mem.add_deps([nodes.File(f) for f in
                  make_depends(target, [ source ],
                               CFLAGS=CFLAGS,
                               CPPPATH=CPPPATH,
                               inc_dirs=includes
                  )
    ])

    cargs = get_config_var('BLDSHARED').split(' ')
    args = util.convert_cmd([cargs[0]] + cargs[1:] +
            CFLAGS + includes +
            target_inc_flag(target, [ source ]) +
            list(includes) +
            ["-c", "-o", target] + [ source ])

    util.ensure_file_dir(target)

    if util.run("GCC (Python Extension)", source, args) != 0:
        Mem.instance().fail()

    return [ nodes.File(target) ]

@util.with_env(CFLAGS=[], LDFLAGS=[])
@mem.memoize
def _link_python_ext(target, objs, CFLAGS, LDFLAGS):
    mem = Mem.instance()
    mem.add_deps(objs)

    cargs = get_config_var('BLDSHARED').split(' ')
    args = util.convert_cmd([cargs[0]] + cargs[1:] +
            CFLAGS + LDFLAGS + ["-o", target] + objs)

    if util.run("GCC Link (Python Extension)", objs, args) != 0:
        Mem.instance().fail()

    return nodes.File(target)


################
# Cython Stuff #
################
class CythonBuilder(object):
    # The regular expression was stolen from the sage setup.py
    _DEP_REGS_PXD = [
        re.compile(r'^ *(?:cimport +([\w\. ,]+))', re.M),
        re.compile(r'^ *(?:from +([\w.]+) +cimport)', re.M),
    ]
    _DEP_REG_DIRECT = \
        re.compile(r'^ *(?:include *[\'"]([^\'"]+)[\'"])', re.M)
    _DEP_REG_CHEADER = \
        re.compile(r'^ *(?:cdef[ ]*extern[ ]*from *[\'"]([^\'"]+)[\'"])', re.M)

    def __init__(self, include_paths):
        self.deps = set()
        self.include_paths = include_paths

    def _find_deps(self, s):
        self._find_deps_pxd(s)
        self._find_deps_cheader(s)
        self._find_deps_direct(s)

    @staticmethod
    def _normalize_module_name(s):
        # Remove as blah at the end
        s = s.split(" as ")[0].strip()

        # Replace all dots except a path seperator
        s = s.replace('.', os.path.sep)

        return s

    def _find_deps_pxd(self, s):
        temp = util.flatten([m.findall(s) for m in self._DEP_REGS_PXD])
        all_matches = util.flatten(
            [ [ s.strip() for s in m.split(',') ] for m in temp] )

        for dep in all_matches:
            dep = self._normalize_module_name(dep)
            dep += '.pxd'
            if dep not in self.deps:
                # Recurse, if file exists. If not, the file might be global
                # (which we currently do not track) or the file
                # might not exist, which is not our problem, but cythons
                for path in self.include_paths + ['']:
                    filename = os.path.relpath(os.path.join(path, dep))
                    if os.path.exists(filename):
                        self._find_deps(open(filename,"r").read())
                    self.deps.add(filename)

    def _find_deps_direct(self, s):
        all_matches = self._DEP_REG_DIRECT.findall(s)

        for dep in all_matches:
            if dep not in self.deps:
                # Recurse, if file exists. If not, the file might be global
                # (which we currently do not track) or the file
                # might not exist, which is not our problem, but cythons
                for path in self.include_paths + ['']:
                    filename = os.path.relpath(os.path.join(path, dep))
                    if os.path.exists(filename):
                        self._find_deps(open(filename,"r").read())
                    self.deps.add(filename)

    def _find_deps_cheader(self, s):
        all_matches = self._DEP_REG_CHEADER.findall(s)

        for dep in all_matches:
            if dep not in self.deps:
                # Recurse, if file exists. If not, the file might be global
                # (which we currently do not track) or the file
                # might not exist, which is not our problem, but cythons
                # TODO: we should track the headers included by this
                # header. But currently we don't
                self.deps.add(dep)

    def build(self, cfile, source):
        self.deps = set((source,))

        # We might also depend on our definition file
        # if it exists
        pxd = os.path.splitext(source)[0] + '.pxd'
        if os.path.exists(pxd):
            self.deps.add(pxd)
            self._find_deps(open(pxd, "r").read())

        self._find_deps(open(source,"r").read())
        self.deps = [ d for d in self.deps if os.path.exists(d) ]

        mem = Mem.instance()
        mem.add_deps([ nodes.File(f) for f in self.deps ])

        args = util.convert_cmd(["cython"] +
                ['-I' + path for path in self.include_paths ] +
                ["-o", cfile, source])

        if util.run("Cython", source, args) != 0:
            Mem.instance().fail()

        return nodes.File(cfile)

@util.with_env(CYTHON_INCLUDE=[])
@mem.memoize
def _run_cython(cfile, source, CYTHON_INCLUDE):
    b = CythonBuilder(CYTHON_INCLUDE)

    return b.build(cfile, source)

##############################
# Main Extension Dispatchers #
##############################
def _python_obj(source, env, build_dir, **kwargs):
    if not os.path.exists(str(source)):
        Mem.instance().fail("%s does not exist" % source)

    target = os.path.join(build_dir, os.path.splitext(source)[0] + '.o')

    return _build_python_obj(target, source,
            env.get("CFLAGS", []),
            env.get("CPPPATH", []),
    )


def _python_cython(source, env, build_dir, **kwargs):
    if not _has_cython:
        raise RuntimeError("Cython is not installed!")

    fname = os.path.basename(source)
    base_target = os.path.join(build_dir, os.path.splitext(fname)[0])

    cfile = _run_cython(base_target + '.c', source,
        env.get("CYTHON_INCLUDE", [])
    )

    return _build_python_obj(base_target + '.o', cfile,
            env.get("CFLAGS", []),
            env.get("CPPPATH", []),
    )

_EXTENSION_DISPATCH = {
    '.c': _python_obj,
    '.pyx': _python_cython,
}

def python_ext(target, sources, env={}, build_dir = "", inplace = False,
               **kwargs):
    """Turn the sources list into a python extension"""

    if not isinstance(sources, list):
        sources = [ sources ]

    mem = Mem.instance()

    build_dir = util.get_build_dir(env, build_dir)

    all_objs = []
    for source in util.flatten(sources):
        ext = os.path.splitext(source)[1].lower()
        if ext not in _EXTENSION_DISPATCH:
            raise ValueError("Don't know how to build extension from source %s"
                    % source)

        objs = _EXTENSION_DISPATCH[ext](source, env or {}, build_dir, **kwargs)

        all_objs.extend(objs)

    target += '.so'

    if not inplace:
        ntarget = os.path.join(build_dir, target)
    else:
        ntarget = target


    if 'CFLAGS' in kwargs:
        CFLAGS = kwargs['CFLAGS'][:]
    elif env is not None:
        CFLAGS = env.get('CFLAGS', [])

    if 'LDFLAGS' in kwargs:
        LDFLAGS = kwargs['LDFLAGS'][:]
    elif env is not None:
        LDFLAGS = env.get('LDFLAGS', [])

    return _link_python_ext(ntarget, all_objs, CFLAGS, LDFLAGS)


