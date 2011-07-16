#!/usr/bin/env python

import sys

from distutils.core import setup

if sys.platform == "win32":
    scripts = ['script/mem.bat',
               'script/runmem.py']
else:
    scripts = ['script/mem']

setup(name='Mem',
      version='1.0',
      description='The mem (memoize) build system',
      author='Scott R Parish',
      author_email='srp@srparish.net',
      packages=['mem',
                'mem.tasks',
                'mem'],
      scripts=scripts,
     )
