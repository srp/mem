Mem: a build system not pulled from the cache of build system convention
========================================================================
:Author: Scott R Parish
:Email: sparish@peak6.com
:Date: 2009-01-20


Why a new build system?
-----------------------

There are no shortage of build systems, what justifies the existence
of yet another one?

Mem is a completely different approach to build systems, one base on
function memoization. Most build systems are based on building up some
static graph of dependencies and then traversing that graph while
minimally rebuilding, propagating changed objects across the graph for
calculating further  steps; usually with very special languages and
sophisticated layers for automatically building the graph, easing
the job of the end user in describing their build.

Practically, mem is different in that:

* the build is simply a script where certain functions are memoized (cached)
* these memoized functions are only rebuilt if one of their inputs changes

The first part means that you can script your build however is most
natural to solve your specific build requirements, and mem sits in the
background and caches and avoids duplicate evaluations (eg needless
rebuilding).

The second part means exactly what it says. This can be startling at
first. For instance, suppose you had a '.c' file, and a build step to
compile it into an object and a build step to link that into a
program. If you make a whitespace change to that '.c' file, such as
add an extra space to the end of a line; the resulting object will
likely be identical (sha1) as the object before this change was
made. Given that mem only builds when things are changed, no relinking
will be done as the object to link will be unchanged!


Memoization
-----------

To best understand the mem build system, we'll have to dive into the
theory of memoization. Bear with us, it's really not complicated and
we'll quickly be on our way to building stuff.

This quote is from wikipedia:

   In computing, memoization is an optimization technique used primarily
   to speed up computer programs by having function calls avoid repeating
   the calculation of results for previously-processed inputs.
 
A classic example of memoization is to allow writing a Fibonacci function
using the mathematical definition, e.g.:

.. math::

   F(n) = \left\{
   \begin{array}{l}
      0\ \mathrm{if}\ n = 0 \\
      1\ \mathrm{if}\ n = 1 \\ 
      F(n-1) + F(n-2)
   \end{array}
   \right.
   
We could write this in Python as::

   def fib(n):
       if n == 0:
           return 0
       elif n == 1:
           return 1
       else:
           return fib(n-1) + fib(n-2)

The problem with this recursive definition is that 'fib(n-1)' and
'fib(n-2)' for large values of 'n' go through most of the same
computational steps, so we're wasting a huge (exponential) amount of
time recomputing the same thing over and over.

One solution is find a way to re-factor the equation so that we can
compute values in a more linear fashion (such as via
iteration). Sometimes this isn't desirable or possible.

Memoization is a different solution. Rather then rewriting the
solution to the equation, we introduce caching, which may look like
this::

   def fib(n, cache={}):
       if n in cache:
           return cache[n]
       if n == 0:
           return 0
       elif n == 1:
           return 1
       else:
           cache[n] = fib(n-1) + fib(n-2)
           return cache[n]

We could abstract the caching so that it doesn't pollute our business
logic and so that we can reuse it::

   def memoize(f):
       cache = {}
       def wrapped_f(arg):
           if arg in cache:
              return cache[arg]
           cache[arg] = f(arg)
           return cache[arg]
       return wrapped_f

   def fib(n):
       if n == 0:
           return 0
       elif n == 1:
           return 1
       else:
           return fib(n-1) + fib(n-2)

   fib = memoize(fib)


And finally, rather then reassigning functions to memoize, we can use
`@decorators <http://www.python.org/dev/peps/pep-0318/>`_ to mark which
functions to memoize::

   @memoize
   def fib(n):
       if n == 0:
           return 0
       elif n == 1:
           return 1
       else:
           return fib(n-1) + fib(n-2)


Building on Memoization
-----------------------

Mem provides you with a handful of tools out of which you create a
memoized based build. The core of which is obviously memoization. Mem
actually provides a 'memoize' function, very similar to the one we
developed in the previous section. The difference is mainly that mem's
memoization has to persist across build invocations, and it has to be
able to account for external data (e.g. files).

We already have enough information to write a simple build task for
creating an object from a '.c' file::

    import mem
    import subprocess
    
    @mem.memoize
    def obj(target, source):
        mem.add_dep(mem.nodes.File(source)) # declare external dependency
        args = ["gcc", "-o", target, source]
        print args                          # let the user know what's happending
        subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
        return mem.nodes.File(target)
    
We call our build function just like you would any other Python
function::

    obj("hello.o", "hello.c")
    
    for src in ["hi.c", "bye.c", "hiagain.c"]:
       obj(src.replace(".c", ".o"), src)

'\@mem.memoize' works largely like the memoize we saw earlier in that
it caches the result as a value on the key of the arguments that
passed to the function. There's a few extra things added:

* 'mem.add_dep()' is called to declare external dependencies, it can
  be called zero or more times anywhere within this function call
  (including sub-function calls). There's also 'mem.add_deps()' which
  takes a list.

  There's nothing special about 'mem.nodes.File()', mem is writen so that
  you can easily define your own types of external dependencies. For
  example, it would be easy to write an S3() external dependency that
  depended on objects in Amazon.com's S3 web-service. A database
  dependency might be another potential.

* A memoized function can return any Python data type, who's value
  will be cached. If the return value is a 'File' (or a list of
  'Files'), then mem will also cache the contents of the files and
  restore them (if needed) on repeated duplicate calls.

Otherwise the above task is doing very straight-forward stuff:

* building up the arguments to call the compiler with
* logging to the user what's happening with the build
* executing the build step--in this case the compiler

Again, there's absolutely no requirement that any of the arguments
be external ('File') dependencies, nor that the result is an external
dependency. Mem will just as happily memoize the following (or even
the 'fib()' we wrote earlier)::

    @mem.memoize
    def render_hello(name):
        return "Hello, %s" % name
    
Environmental Impacts
---------------------

Many build systems have some concept of an environment. For example,
it would be really nice if the 'obj()' function we wrote earlier would
allow us to pass extra flags to the compiler.

Naively we could create an environment out of a dictionary and just
pass that into each build function (That is bad, don't do it. See below)::

   import mem
   import subprocess

   @mem.memoize
   def obj(target, source, env={}):
       mem.add_dep(mem.nodes.File(source)) # declare external dependency
       cflags = env.get("CFLAGS", [])
       args = ["gcc", "-o", target, source] + cflags
       print args                          # let the user know what's happening
       subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
       return mem.nodes.File(target)

That works, but isn't optimal because now if the environment key
"SWIG_FLAGS" changes, all the 'obj()' calls will be re-ran, even
though they don't make use of that part of the environment.

To avoid such problems, mem has defined another helpful decorator for
dealing with environment variables:
'\@mem.util.with_env()'. 'with_env()' takes a list of environment keys
(and defaults for if they are not found), pulls those keys out of the
environment and passes only those to the memoized part of the
function.

Here's a better version of 'obj()' using 'with_env()'::

    import mem
    import subprocess
    
    @mem.util.with_env(CFLAGS=[])         # only pass-in CFLAGS from the environment
    @mem.memoize
    def obj(target, source, CFLAGS):
        mem.add_dep(mem.nodes.File(source)) # declare external dependency
        args = ["gcc", "-o", target, source] + CFLAGS
        print args                          # let the user know what's happending
        subprocess.Popen(args, stdin = PIPE, stdout = PIPE)
        return mem.nodes.File(target)


'mem.util.with_env' should always come before 'mem.memoize' or it
won't have the full desired effect.

There's nothing that ties 'mem.util.with_env' into 'mem.memoize'. They
are useful together, but 'mem.util.with_env' can be just as useful
alone.

The 'Env' class
~~~~~~~~~~~~~~~

Mem does provide an 'mem.util.Env' class that extends the base 'dict'
class. It's not very exciting; it mainly provides:

* Access using attributes: e.g. 'env.CFLAGS' is the same as
  'env["CFLAGS"]'

* 'subst()' method which allows for string expansion using the
  environment. For instance if 'env.ROOT = "/foo"' then,
  'env.subst("%(ROOT)s/bar")' would return '/foo/bar'

* 'replace()' method which allows for easily setting/replacing
  environment entries, in mass, along with automatic 'subst()'
  expansion


Memfiles
--------

Startup
~~~~~~~

When mem is ran, it initializes itself, searches down the directory
tree (towards the root) for the first directory with a 'MemfileRoot'
in it, it imports this file, and then runs the 'build()' function from
it, which should take no arguments.


Sub-Directories
~~~~~~~~~~~~~~~

Mem has primitive support for allowing a build to span multiple
directories. The core of this functionality is the form
'mem.subdir(mydir)', which will import the file 'mydir/Memfile'. It
returns a wrapped module such that anytime you call a function on it:

* changes env.cwd and the process's cwd to "mydir"
* calls the function, passing any arguments given
* restores env.cwd and the process's cwd

The intent behind changing the directory is to make things like
`glob <http://docs.python.org/library/glob.html#glob.glob>`_ more
convenient for the user writing the script.

Build functions and CWD
^^^^^^^^^^^^^^^^^^^^^^^
Build functions generally print to the user any commands that are
being run, so the user know where the build broke, or how its
proceeding. As far as possible it's suggested that, build functions
should strive to accept absolute or relative paths, but only run and
print using absolute paths.

The rational for doing so is that a user can then, from any directory,
copy and paste an offending command without having to figure out what
directory he has to be in to run it.

Writing your own build functions
--------------------------------

Mem basically just provides some core functionality which you can use
to build your own build functions with. Mem does ship with a few example
build functions which are much more full featured (great for
complicated use, but harder to understand).

In general, here's some of the things you might want to consider when
writing a new build function:

* Scanning: if the source(s) can depend on other files, probably
  recursivelly, the build will only be correct if you correctly scan
  and identify all of these dependencies and declare them using
  'mem.add_dep()'. It doesn't have to be very hard, some compilers
  (eg gcc, swig) come with something like 'make depends' which is a
  mode where they will automatically spit out a list of dependencies
  (read the manual for gcc's '-M' flag). Many other dependencies can
  be easily parsed out by a fairly simple regular expression.

* Returning all targets: just as important as scanning to get all
  included dependencies is returning all of the results of a build
  function. Lets say your compiler produces two output files, but you
  only return one of those from your build function, but use the
  second file later in your build; since mem wasn't notified that the
  second file was a result, it won't restore it, meaning that later on
  in the build it could be stale or even missing.

* Try to keep the memoized functions as simple as possible--typically
  they are leaf functions. Not everything has to be memoized
  though, so a common practice is to have large complicated
  non-memoized functions that are written in terms of several simple,
  primitive memoized functions. For example, in the 'obj()' we
  developed in this document, it would be handy if it automatically
  guessed the target name if none was given. It would be best to do
  such calculation in an outer non-memoized function which then calls
  the simpler memoized 'obj()'.

* Use common sense and good programming style. Mem leaves you with the
  full programming language in-tact; there's no excuse for using bad
  practices you wouldn't do in your normal programming.


Exceptions
~~~~~~~~~~

When we said that "Mem leaves the full programming language in-tact",
there's no better way to illustrate this then exceptions. You can
raise and catch exceptions just like you normally would in python. This
can be very useful, for example, you might still want to run your
documentation generation and cscopes indexer even if the rest of the
build fails.

