from enum import IntEnum

SIZEOFBOARD = 15

class character(IntEnum):
    EMPTY = 0
    BLACK = 1
    WHITE = 2

def noSix():
    return 0

RULES = {"No 6": noSix}