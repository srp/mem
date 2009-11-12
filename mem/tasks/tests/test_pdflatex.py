#!/usr/bin/env python
# encoding: utf-8

from nose.tools import *

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))

import mem

from pdflatex import PDFLatexBuilder

class _PDFLatexTest(object):
    def setUp(self):
        self.c = PDFLatexBuilder()


class Test_LatexDependecyTracking(_PDFLatexTest): # {{{
    def test_input_without_ext(self):
        rv = self.c._find_potential_latex_deps("""\input{hallo}""")
        eq_(rv, ['hallo.tex', 'hallo.ltx', 'hallo.latex', 'hallo'])
    def test_input_with_ext(self):
        rv = self.c._find_potential_latex_deps("""\input{hallo.latex}""")
        eq_(rv, ['hallo.latex'])

    def test_include_without_ext(self):
        rv = self.c._find_potential_latex_deps("""\include{hallo}""")
        eq_(rv, ['hallo.tex', 'hallo.ltx', 'hallo.latex', 'hallo'])
    def test_include_with_ext(self):
        rv = self.c._find_potential_latex_deps("""\include{hallo.latex}""")
        eq_(rv, ['hallo.latex'])

    def test_include_notonsingle_line(self):
        rv = self.c._find_potential_latex_deps(
            r"""$\alpha$ \include{hallo.latex}""")
        eq_(rv, ['hallo.latex'])
    def test_include_notonsingle_line2(self):
        rv = self.c._find_potential_latex_deps(
            r"""\texttt{\input{MemfileRoot}}""")
        eq_(rv, ['MemfileRoot.tex', 'MemfileRoot.ltx',
                 'MemfileRoot.latex', 'MemfileRoot'])

    def test_ignorecomments(self):
        rv = self.c._find_potential_latex_deps(
            r"""$\alpha$ % \include{hallo.latex}""")
        eq_(rv, [])

    def test_realworld_example(self):
        s = """
\documentclass[a4]{rvmrt}

\input{header.tex}

\title{something}
\author{James. T. Kirk}

\begin{document}

\maketitle

\input{titlepage.tex}
\input{first_sec.tex}
\input{about_the_sun}
\input{people_on_the_moon}
\input{python.tex}
\input{long_story_short.tex}

\pagebreak{}
\appendix{}

%% Include this
\input{Some_Appendix.tex} % A comment
%% do not include this
% \input{do_not_include.tex} % A comment

\end{document}
"""
        rv = self.c._find_potential_latex_deps(s)
        print "rv: %s" % (rv)
        eq_(rv.pop(0), 'header.tex')
        eq_(rv.pop(0), 'titlepage.tex')
        eq_(rv.pop(0), 'first_sec.tex')
        eq_(rv.pop(0), 'about_the_sun.tex')
        eq_(rv.pop(0), 'about_the_sun.ltx')
        eq_(rv.pop(0), 'about_the_sun.latex')
        eq_(rv.pop(0), 'about_the_sun')
        eq_(rv.pop(0), 'people_on_the_moon.tex')
        eq_(rv.pop(0), 'people_on_the_moon.ltx')
        eq_(rv.pop(0), 'people_on_the_moon.latex')
        eq_(rv.pop(0), 'people_on_the_moon')
        eq_(rv.pop(0), 'python.tex')
        eq_(rv.pop(0), 'long_story_short.tex')

        eq_(rv.pop(0), 'Some_Appendix.tex')

        eq_(len(rv), 0)
# }}}

class Test_ImageDepdencyTracking(_PDFLatexTest):
    def test_simple(self):
        rv = self.c._find_potential_graphic_deps(
            "\includegraphics{pics/picture.pdf}"
        )
        eq_(rv, ["pics/picture.pdf"])
    def test_simple_with_options_no_whitespaces(self):
        rv = self.c._find_potential_graphic_deps(
            "\includegraphics[width=8cm]{pics/picture.pdf}"
        )
        eq_(rv, ["pics/picture.pdf"])
    def test_simple_with_options_many_whitespaces(self):
        rv = self.c._find_potential_graphic_deps(
            "\includegraphics [width=8cm]  {pics/picture.pdf}"
        )
        eq_(rv, ["pics/picture.pdf"])

    def test_no_extension(self):
        rv = self.c._find_potential_graphic_deps(
            "\includegraphics [width=8cm]{p}"
        )
        eq_(rv, ['p.pdf', 'p.eps', 'p.png', 'p.jpg', 'p.tif', 'p.bmp'])

    def test_not_on_single_line(self):
        rv = self.c._find_potential_graphic_deps(
            "$beta$ \includegraphics [width=8cm]  {pics/picture.pdf}"
        )
        eq_(rv, ["pics/picture.pdf"])

    def test_commented(self):
        rv = self.c._find_potential_graphic_deps(
            "$beta$ % \includegraphics [width=8cm]  {pics/picture.pdf}"
        )
        eq_(rv, [])

class Test_ValidateTarget(_PDFLatexTest):
    def test_NoneTarget(self):
        eq_(self.c._check_target("blah.tex", None), "blah.pdf")
    @raises(ValueError)
    def test_InvalidTarget(self):
        self.c._check_target("blah.tex", "Humpa.ups")


