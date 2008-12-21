
import mem.tasks.c
import mem.nodes
import os

def build():
    env = mem.nodes.Env(c = mem.tasks.c)
    env.c.prog("hello",
               env.c.obj("hello.o", "hello.c"),
               env.c.obj("main.o", "main.c"))
