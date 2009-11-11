import os
import subprocess
from subprocess import PIPE
import sys
from threading import Thread

import mem
from mem_.nodes import File
from mem_.util import _open_pipe_

import re

class PDFLatexBuilder(object):
    _LATEX_DEPS = re.compile(r'^\s*\\(?:input|include){(.*)}',
            re.IGNORECASE | re.MULTILINE)

    def __init__(self):
        # TODO: is this really needed? Can we not get mem to remember
        # which dependencies we already added? most likely yes.
        self._deps = []

    def _run_pdflatex(self, source_list, args):
        code,stderr,stdout = mem.util.run_return_output_no_print(
            "PDFLATEX", source_list, _open_pipe_, args)
        if code is not 0:
            mem.fail("PDFLatex failed!")

        return stderr, stdout

    def _need_rerun(self, output):
        if output.find("Rerun to get cross-references right") != -1:
            return True


    def _find_potential_deps(self, s):
        """
        Parse the given string for input or include dependencies. Return
        a list of potential filenames to look for:

        \input{blah} -> blah, blah.tex, blah.ltx, blah.latex
        \input{blah.tex} -> blah.tex

        This function completely ignores the includeonly directive.
        """
        rv = []
        for m in self._LATEX_DEPS.findall(s):
            if os.path.splitext(m)[1] is '':
                rv.extend( (m + '.tex', m + '.ltx', m + '.latex', m) )
            else:
                rv.append(m)

        return rv

    def _validate_target(self, target):
        if os.path.splitext(target)[1].lower() != '.pdf':
            raise ValueError("%s is not a valid target for this builder"
                    % target)

        return target

    def _check_target(self, source, target):
        """
        If the target is None, construct a filename from the source
        given. Then validate the target file name
        """
        if target is None:
            target = os.path.splitext(source)[0] + '.pdf'

        return self._validate_target(target)

    def _find_dependencies(self, s):
        """
        This function finds all (Tex) dependencies for this tex source file.
        This are all files included or imported into the tex file;
        the function recursively tracks all dependencies down.
        """
        for fname in self._find_potential_deps(s):
            if os.path.exists(fname) and fname not in self._deps:
                self._deps.append(fname)
                self._find_dependencies(open(fname,"r").read())

    def build(self, mem, source, target=None, env=None,
              build_dir=None, **kwargs):
        BuildDir = mem.util.get_build_dir(env, build_dir)

        if not isinstance(source, (str,File)):
            # TODO: or should this be a mem.fail
            raise RuntimeError("Only takes a single source tex file!")

        mem.add_dep(mem.util.convert_to_file(source))
        self._find_dependencies(open(source, "r").read())

        # Add all the recursively found dependencies
        for d in self._deps:
            mem.add_dep(mem.util.convert_to_file(d))

        args = mem.util.convert_cmd(['pdflatex', source])

        targer = self._check_target(source, target)

        mem.util.ensure_file_dir(target)

        while 1:
            stderr, stdout = self._run_pdflatex(source_list, args)
            if not self._need_rerun(stderr):
                break

        return File(target)

@mem.memoize
def pdflatex(*args, **kwargs):
    builder = PDFLatexBuilder()

    builder.build(mem, *args, **kwargs)

