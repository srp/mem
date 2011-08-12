
Mem: Designing a build system out of the Memoization of build steps
===================================================================
:Author:  Scott R Parish
:Email:   sparish@peak6.com
:Date:    2008-12-31

.. highlight:: python


Abstract
--------

Problems can be very difficult or trivial depending on the approach and
algorithms used to solve them. In this document we'll go through the
thought process of creating a build system out of the memoization of
function calls. I believe this approach will best lead to an
understanding of how 'mem' works, and how to use and extend
it. Arguably this new approach to building results in more elegant,
simpler, easier to use build systems than typically seen approaches
to build systems.

Background on Memoization
-------------------------

`Memoization <http://en.wikipedia.org/wiki/Memoization>`_ is an
optimization technique which caches the result of a function by its
input arguments, thus allowing future calls using identical arguments
to immediately return the cached value instead of repeating the (most
likely expensive) evaluation of the function. Obviously this only
works if the function is pure--meaning no side effects and the same
return value for calls of identically valued arguments.

Memoization can either happen either automatically or manually. By
automatic, the programmer will somehow annotate that a function is to
be memoized and the language or a library he is working with will take
the existing function and automatically wrap memoization around
it. Without the aid of linguistic or library support, a function can
often be modified so that it does its own memoization. The downside is
obviously that of complicating the function.

Properties needed for build
---------------------------

`SCons <http://www.scons.org>`_ and similar build systems have already
demonstrated that builds could be composed using function or method
evaluation. Obviously to use memoization, we'll have to find a way to
make these pure, or effectively pure. When viewed linguistically,
build steps are not pure as they involve mutations on the file
system. However, if we define pure to include the file results of a
build step, then we can consider it to be pure as long as we can
include such in the memoization process.

Additionally, since we're memoizing across multiple process invocations,
we'll also have to find a way to consistently and durably hash and
cache.

Memoization for a build system
------------------------------

The syntax
~~~~~~~~~~

We'd prefer automatic memoization. Rather than designing a new
language for builds, we'll take a similar approach to SCons or
Waf, and use Python as a language for expressing the steps in
builds. Python's decorators give a perfect mechanism to support
automatic memoization, as we should be able to express something like::

    @memoize
    def obj(target, source, ...):
        ...

Which is syntactical sugar for::

    def obj(target, source, ...):
        ...
    obj = memoize(obj)

We can write memoize to look something like the following::

    def memoize(origf):
        def newf(*args, **kwargs):
            # at this point we've captured the calling args and can
            # hash them and check for a previous call
            h = hash(origf, args, kwargs)
            if (cache.has_key(h)):
                return cache[h]
            else:
                r = origf(*args, **kwargs)
                cache[h] = r
                return r
        return newf

This defines and returns a new function that creates a closure around
the old function. When called, it grabs the arguments, checks them for
a cache hit, and then if needed, calls the original function--caching
its result.

While this works, it doesn't take into account the file system aspect
of these functions. For example, if a file is used as an input, the
contents of that file should be included in the hash; if a file is a
result, its contents should be included as part of the result.

The algorithm for memoization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We need to know about the file inputs and results. For the argument
inputs, we could scan each one and try to find anything that looks
like a file and automatically include that in the hash. Unfortunately
this would either mean that the arguments need to be simple or that we
would need to do complicated deep object traversal. This would also
prevent a build function from composing the path to its file out of a
number of arguments. It also wouldn't allow us to distinguish inputs
from outputs (the later which should not be included in the
hash). Thus we rule this option out.

Instead we'll require that each function declare any input files that
it uses. We can do this by passing the build function an extra
parameter with such a method on it, thus such a build function could
look like::

    def obj(mem, target, source, ...):
        mem.add_dep(source)
        ...

This is now going to complicate our memoize() function. When it goes
to create the hash to store a result, it will need to grab the list of
dependencies and hash the contents of each one. Even worse, when it
goes to check if a given entry has already been cached, it won't have
run the function yet, so it won't already know the dependencies, so it
can't compute the hash.

A simple solution is to cache the list of dependencies. Thus the
(simplified/pseudofied) algorithm for the memoization can be expressed
as::

    # find cached dependencies (if any)
    h1 = hash(origf, args, kwargs)
    if not deps_cache.has_key(h1):
        return run()
    deps = deps_cache[h1]
    
    # find result (if any)
    h2 = hash(origf, args, kwargs, [dep.hash() for dep in deps])
    if not r_cache.has_key(h2):
        return run()
    
    # restore result (if needed)
    r = r_cache[h2]
    if hasattr(r, restore):
        r.restore()
    return r


The first step uses all of the runtime available information to lookup
the list of dependencies that was declared last time function was
run. The second step creates a further hash, including the
dependencies (eg hashing the contents of dependant files), which is
used to try to find the result. The final step is to restore (eg
restore the contents of resulting files) and return the result.

Finally, 'run()' might look something like::

    r = origf(*args, **kwargs)
    r.store()
    h2 = hash(origf, args, kwargs, [dep.hash() for dep in deps])
    r_cache[h2] = r
    h1 = hash(origf, args, kwargs)
    deps_cache[h1] = deps

Hashing and durability
~~~~~~~~~~~~~~~~~~~~~~

Python makes both of these fairly trivial. For hashing we'll either
call a hash() method on each object (if supported), or fall back on
using Python's pickle.

For durability we'll write a pickle into a file named with the hash.

A File class
~~~~~~~~~~~~

The algorithm developed prior assumed that the dependencies were some
kind of object that supported a hash() method, and that the results
were some kind of objects that support a store() and restore(),
method. Let's look at what a basic File class might look like to
support both of these. As a simple way of caching large files, we'll
use a git repo::

   class File:
       def __init__(self, path):
           self.path = path

       #
       # Methods used when acting as a dependency
       #

       def hash(self):
           with open(self.path) as f:
               return sha1(f.read()).hexdigest()

       #
       # Methods used when acting as a result
       #

       def store(self):
           self.git_hash = git.hash_object("-w", self.path).strip()

       def restore(self):
           git.cat_file("blob", self.git_hash, stdout=open(self.path, "wb"))


The reason we implement both of these in the same class is that
results from one build function often end up being dependencies of
another, consider::

    hello_o = obj("hello.o", "hello.c", ...)
    prog("hello", hello_o)


Environments
------------

Environments do not have to be tied into the core of a build
algorithm. For example, a dict() created by the user would almost
suffice, eg::

    env = {'CC': 'gcc',
           'CFLAGS': '-Wall -O2'
           #...
          }
    hello_o = obj("hello.o", "hello.c", env)

This almost works, but has two problems. First off, there's no
tracking which parts of the environment each task used, so if
something unrelated (such as 'SWIGFLAGS') changes, everything that
accepts the environment has to be rebuilt. Secondly, non-toplevel
functions can not be pickled, so if any such functions are placed in
the environment, an exception will be raised.

There are several ways this could be approached. One could be to
require the caller to explicitly pass individual arguments, eg::

    hello_o = obj("hello.o", "hello.c", CC=env['CC'], CFLAGS=env['CFLAGS'], ...)

This is obviously needlessly verbose and tedius for users; we could
require that the task register these (much like how it registers
dependencies) but then we also have to provide some way of
special-casing that the environment shouldn't get included in the
hashing done with the rest of the arguments.

We decide to go with the first option, but create a decorator,
with_env(), to automate the environment expansion, allowing::

    @with_env(CC="gcc", CFLAGS=[], ...)
    @memoize
    def obj(target, source, CC, CFLAGS):
        ...

with_env wraps the function so that the user can write code such as::

    hello_o = obj("hello.o", "hello.c", env=env)

It then pulls out of the environment the values for keys specified on
the decoration, or the default values if such isn't found in the
environment.

We now will only include in the hash the values from the environment
that were used for that specific step. We're also did it without
having to extend the core althorithm.

Summary
-------

Using the above approach allows for a very simple, elegant, easy build
core. We've shown how it can be used with core python datastructures
and external files, it could just as easily be extended to work
against database entries or external systems such as REST services
such as S3 or state machines. Layering functionally on top of this
core allows for just as rich of build expressions, with the full power
of the underlying programming language intact.

In real world use, it has been seen to function correctly, and be
faster and easier to develop and maintain build tasks on than SCons;
it also runs faster than such.
