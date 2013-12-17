def f():
    g()

def g():
    f()

class file():
    def __init__(notself, x):
        notself.y = x
        x1 = x
    
