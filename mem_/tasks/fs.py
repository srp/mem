import os
import mem

def symlink(target, sources):
    is_dir = os.path.isdir(target)
    for s in sources:
        if is_dir:
            t = os.path.join(target, os.path.basename(s))
        else:
            t = target
        if not os.path.islink(t) or os.readlink(t) != s:
            print "ln -sf", t, s
            if os.path.exists(t):
                os.unlink(t)
            os.symlink(s, t)
