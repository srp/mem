import os
import mem
import shutil

class Error(EnvironmentError):
    pass

def copytree(src, dst, symlinks=False, ignore=None):
    returned = []
    names = []

    if os.path.isdir(src):
        names = os.listdir(src)
    else:
        names = [os.path.basename(src)]
        src = os.path.dirname(src)

    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    try:
        os.makedirs(dst)
    except OSError:
        pass

    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        print dstname
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                returned.extend(copytree(srcname, dstname, symlinks, ignore))
            elif not srcname == dstname:
                shutil.copy2(srcname, dstname)
                returned.append(dstname)
        except (IOError, os.error), why:
            errors.append((srcname, dstname, str(why)))
        except Error, err:
            errors.extend(err.args[0])
    try:
        shutil.copystat(src, dst)
    except OSError, why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise Error, errors

    return returned


@mem.memoize
def copy(target, source):
    print target, source
    return always_copy(target, source)


def always_copy(target, source):
    """ copies the sources to the target """
    if not isinstance(source, list):
        source = [source]
    print "source", source
    returned = []
    for src in source:
        print "copying %s to %s" % (src, target)
        returned.extend(copytree(src, target))

    return [mem.nodes.File(f) for f in returned]


