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
    import re
    _has_cython = True
except ImportError:
    _has_cython = False

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

    def __init__(self):
        self.deps = set()

    def _find_deps(self, s):
        self._find_deps_pxd(s)
        self._find_deps_cheader(s)
        self._find_deps_direct(s)

    def _find_deps_pxd(self, s):
        temp = util.flatten([m.findall(s) for m in self._DEP_REGS_PXD])
        all_matches = util.flatten(
            [ [ s.strip() for s in m.split(',') ] for m in temp] )

        for dep in all_matches:
            dep += '.pxd'
            if dep not in self.deps:
                # Recurse, if file exists. If not, the file might be global
                # (which we currently do not track) or the file
                # might not exist, which is not our problem, but cythons
                if os.path.exists(dep):
                    self._find_deps(open(dep,"r").read())
                self.deps.add(dep)

    def _find_deps_direct(self, s):
        all_matches = self._DEP_REG_DIRECT.findall(s)

        for dep in all_matches:
            print "dep: %s" % (dep)
            if dep not in self.deps:
                # Recurse, if file exists. If not, the file might be global
                # (which we currently do not track) or the file
                # might not exist, which is not our problem, but cythons
                if os.path.exists(dep):
                    self._find_deps(open(dep,"r").read())
                self.deps.add(dep)

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

        self._find_deps(open(source,"r").read())

        mem = Mem.instance()
        mem.add_deps([ nodes.File(f) for f in self.deps])

        args = util.convert_cmd(["cython"] +
                ["-o", cfile, source])

        if util.run("Cython", source, args) != 0:
            Mem.instance().fail()

        return nodes.File(cfile)

@mem.memoize
def _run_cython(cfile, source):
    b = CythonBuilder()

    return b.build(cfile, source)

##############################
# Main Extension Dispatchers #
##############################
def _python_obj(source, env, build_dir, **kwargs):
    if not os.path.exists(str(source)):
        Mem.instance().fail("%s does not exist" % source)

    target = build_dir + os.path.splitext(source)[0] + '.o'

    return _build_python_obj(target, source,
            env.get("CFLAGS", []),
            env.get("CPPPATH", []),
    )


def _python_cython(source, env, build_dir, **kwargs):
    if not _has_cython:
        raise RuntimeError("Cython is not installed!")

    base_target = build_dir + os.path.splitext(source)[0]
    cfile = _run_cython(base_target + '.c', source)

    return _build_python_obj(base_target + '.o', cfile,
            env.get("CFLAGS", []),
            env.get("CPPPATH", []),
    )

_EXTENSION_DISPATCH = {
    '.c': _python_obj,
    '.pyx': _python_cython,
}

def python_ext(target, sources, env=None, build_dir = "", **kwargs):
    """Turn the sources list into a python extension"""

    if not isinstance(sources, list):
        sources = [ sources ]

    mem = Mem.instance()

    all_objs = []
    for source in util.flatten(sources):
        ext = os.path.splitext(source)[1].lower()
        if ext not in _EXTENSION_DISPATCH:
            raise ValueError("Don't know how to build extension from source %s"
                    % source)

        objs = _EXTENSION_DISPATCH[ext](source, env or {}, build_dir, **kwargs)

        all_objs.extend(objs)

    target += '.so'

    build_dir = util.get_build_dir(env, build_dir)
    ntarget = os.path.join(build_dir, target)


    if 'CFLAGS' in kwargs:
        CFLAGS = kwargs['CFLAGS'][:]
    elif env is not None:
        CFLAGS = env.CFLAGS[:]
    else:
        CFLAGS = []

    if 'LDFLAGS' in kwargs:
        LDFLAGS = kwargs['LDFLAGS'][:]
    elif env is not None:
        LDFLAGS = env.LDFLAGS[:]
    else:
        LDFLAGS = []

    return _link_python_ext(ntarget, all_objs, CFLAGS, LDFLAGS)


