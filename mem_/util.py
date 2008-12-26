from string import split
import os
import imp
import sys


def get_build_dir(env, arg_func):
    """ return a valid build directory given the environment """
    import mem

    if arg_func and type(arg_func) == str:
        return arg_func
    elif arg_func:
        return arg_func(env)

    try:
        func = env.BUILD_DIR_FUNC

        if func:
            return func(env)
    except AttributeError:
        pass

    try:
        if not env.BUILD_DIR:
            return src_dir
    except AttributeError:
        pass

    root = mem.root
    src_dir = mem.cwd

    if not src_dir.startswith(root):
        mem.fail("source dir (%s) is not a subdir of root (%s) "
                 "unable to generate a build path" % src_dir, root)

    sub_dir = src_dir[len(root) + 1:]


    dir = os.path.join(root, env.BUILD_DIR, sub_dir)

    try:
        os.makedirs(dir)
    except OSError:
        pass

    return dir


def flatten(l, ltypes=(list, tuple)):
    """ Flatten a list type into single list """
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)


def convert_to_files(src_list):
    """ Convert a list of mixed strings/files to files """
    from mem_.nodes import File
    nlist = []
    for src in src_list:
        if isinstance(src, File):
            nlist.append(src)
        else:
            nlist.append(File(src))
    return nlist

def convert_to_file(src):
    from mem_.nodes import File
    if isinstance(src, File):
        return src
    else:
        return File(src)

def convert_cmd(lst):
    return [str(a) for a in lst]

def search_file(filename, paths):
    """Given a search path, find file
    """
    if os.path.exists(filename):
        return filename

    if isinstance(paths, str):
        paths = paths.split(os.path.pathsep)

    for path in paths:
        fp = os.path.join(path, filename)
        if os.path.exists(fp):
            return fp
    return None


def with_env(**kwargs):
    def decorator(f):
        def new_f(*args, **fkwargs):
            if fkwargs.has_key("env"):
                fenv = fkwargs.pop("env")
                for k in kwargs.keys():
                    if not fkwargs.has_key(k):
                        if fenv.has_key(k):
                            fkwargs[k] = fenv[k]
                        else:
                            fkwargs[k] = kwargs[k]
            return f(*args, **fkwargs)
        return new_f
    return decorator

def ensure_file_dir(path):
    try:
        os.makedirs(os.path.dirname(path))
    except OSError:
        pass

def ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError:
        pass

def import_module(name, fname=None):
    if not fname:
        fname = name + ".py"

    sys.path.append("./")
    m = imp.new_module(name)
    m.__file__ = fname
    execfile(fname, m.__dict__, m.__dict__)
    return m
