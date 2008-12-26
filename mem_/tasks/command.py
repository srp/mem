import commands
import mem

@mem.memoize
def command(cmd):
    always_command(cmd)


def always_command(cmd):
    """ Runs the specified command """
    print cmd
    (stat, out) = commands.getstatusoutput(cmd)
    if stat:
        mem.fail(cmd + ":" + out)

    return None


