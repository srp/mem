import os
from subprocess import Popen, PIPE

## a class allowing easy interaction with git via python
##
## based loosely on ideas from John Wiegley's gitshelve.py:
##   git://github.com/jwiegley/git-issues.git

class GitRepoError(Exception):
    def __init__(self, args, kwargs, stderr):
        self.args = args
        self.kwargs = kwargs
        self.stderr = stderr

    def __str__(self):
        return "git %s %s: %s" % (self.args, self.kwargs, self.stderr)

class GitRepo(object):
    def __init__(self, repo_dir = None, env = None):
        if not env:
            self.env = os.environ.copy()
        else:
            self.env = env.copy()

        self.env["GIT_DIR"] = repo_dir

        if not os.path.exists(repo_dir):
            self.init("--bare", "--quiet")

    def call(self, *args, **kwargs):
        stdin = kwargs.get("stdin", PIPE)
        stdout = kwargs.get("stdout", PIPE)

        p = Popen(("git",) + args,
                  env = self.env,
                  stdin=stdin, stdout=stdout, stderr=PIPE)

        out = None
        if stdout == PIPE:
            out = p.stdout.read()

        r = p.wait()
        if r != 0:
            raise GitRepoError(args, kwargs, p.stderr.read())

        return out

    def __getattr__(self, name):
        def call(*args, **kwargs):
            return self.call(name.replace("_", "-"), *args, **kwargs)
        return call
