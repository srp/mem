
import mem.tasks.c
import mem.nodes
import os

def build():
    env = mem.nodes.Env(c = mem.tasks.c,
                        CFLAGS = ["-O1", "-Wall", "-Wextra"])
    env.c.prog("hello",
               objs = [env.c.obj("hello.o", "hello.c", env=env),
                       env.c.obj("main.o", "main.c", env=env)],
               env=env)
