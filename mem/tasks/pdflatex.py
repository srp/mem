
import os
import subprocess
from subprocess import PIPE
import sys
from threading import Thread

import mem
from mem._mem import Mem

import re

# TODO: support for bibtex
# TODO: support for makeindex
# TODO: support for graphicspath
# TODO: support for includeonly
# TODO: temporary files should be created in the temp directory. For this 
#       to work, we had to copy all latex files into the dir and run the 
#       commands there. That is because tex can't be told where to put temp files.

# Nice reading for correct builds:
# http://vim-latex.sourceforge.net/documentation/ 
#   latex-suite/compiling-multiple.html

class PDFLatexBuilder(object):
    _GRAPHIC_EXTENSIONS = [ '.pdf', '.eps', '.png', '.jpg', '.tif', '.bmp' ]
    _LATEX_DEPS = re.compile(r'^[^%\r\n]*\\(?:input|include){(.*?)}',
            re.IGNORECASE | re.MULTILINE)
    _GRAPHIC_DEPS = re.compile(
        r'^[^%\r\n]*\\(?:includegraphics)(?:\s*\[.*\]\s*)?{(.*?)}',
            re.IGNORECASE | re.MULTILINE
    )

    def __init__(self):
        # TODO: is this really needed? Can we not get mem to remember
        # which dependencies we already added? most likely yes.
        self._deps = []

    def _run_pdflatex(self, source_list, args):
        code,stderr,stdout = mem.util.run_return_output_no_print(
            "PDFLATEX", source_list, mem.util._open_pipe_, args)
        if code is not 0:
            print stderr
            Mem.instance().fail("PDFLatex failed!")

        return stderr, stdout

    def _need_rerun(self, output):
        if output.find("Rerun to get cross-references right") != -1:
            return True

    def _find_potential_latex_deps(self, s):
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

    def _find_potential_graphic_deps(self, s):
        """
        See _find_potential_latex_deps docstring

        This function completely ignores the graphicspath directive.
        """
        rv = []
        for m in self._GRAPHIC_DEPS.findall(s):
            if os.path.splitext(m)[1] is '':
                rv.extend(m + ext for ext in self._GRAPHIC_EXTENSIONS)
            else:
                rv.append(m)

        return rv

    def _find_dependencies(self, s):
        """
        This function finds all (Tex) dependencies for this tex source file.
        This are all files included or imported into the tex file;
        the function recursively tracks all dependencies down.
        """
        # Search for graphic dependencies
        for fname in self._find_potential_graphic_deps(s):
            if os.path.exists(fname) and fname not in self._deps:
                self._deps.append(fname)

        # Find latex dependencies
        for fname in self._find_potential_latex_deps(s):
            if os.path.exists(fname) and fname not in self._deps:
                self._deps.append(fname)
                self._find_dependencies(open(fname,"r").read())

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


    def build(self, mem, source, target=None, env=None,
              build_dir=None, **kwargs):
        BuildDir = mem.util.get_build_dir(env, build_dir)

        if not isinstance(source, (str,mem.nodes.File)):
            # TODO: or should this be a mem.fail
            raise RuntimeError("Only takes a single source tex file!")

        Mem.instance().add_dep(mem.util.convert_to_file(source))
        self._find_dependencies(open(source, "r").read())

        # Add all the recursively found dependencies
        for d in self._deps:
            Mem.instance().add_dep(mem.util.convert_to_file(d))

        args = mem.util.convert_cmd(['pdflatex', "-interaction=nonstopmode",
                    source])

        target = self._check_target(source, target)

        mem.util.ensure_file_dir(target)

        # Finally, run PDFLatex
        while 1:
            stderr, stdout = self._run_pdflatex(source, args)
            if not self._need_rerun(stderr):
                break

        return mem.nodes.File(target)

@mem.memoize
def pdflatex(*args, **kwargs):
    builder = PDFLatexBuilder()

    return builder.build(mem, *args, **kwargs)

