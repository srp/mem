import os

import mem

def get_build_dir(env, func):
    """ return a valid build directory given the environment """

    if func and type(func) == str:
        return func
    elif func:
        return func(env)

    root = mem.root
    src_dir = mem.cwd

    if not env.BUILD_DIR:
        return src_dir

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
