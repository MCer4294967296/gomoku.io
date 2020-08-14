from rules import *
import random
class Game:

    def __init__(self, rules = []):
        self.grid = []
        self.rules = rules.copy()
        for i in range(SIZEOFBOARD):
            row = [character.EMPTY] * SIZEOFBOARD
            self.grid.append(row)
        self.last = character.WHITE
    

    def down(self, p, loc):
        """ returns
            0 if successful,
            1 if winning,
            2 if illegal position,
            3 if not empty,
            4 if illegal player id,
            5 if wrong player moving
            <0 for various rules
        """
        if p == self.last:
            return 5
        r, c = loc
        if not self.validLoc(loc):
            return 2
        if p is not character.BLACK and p is not character.WHITE:
            return 4
        if self.grid[r][c] is not character.EMPTY:
            return 3
        restricted = self.otherRules(loc, p)
        if restricted:
            return restricted
        self.grid[r][c] = p
        if self.checkIfWinningAt(loc):
            return 1
        self.last = p
        return 0


    def otherRules(self, loc, p):
        for rule in self.rules:
            res = RULES[rule](loc, p)
            if not res:
                return res
    

    def checkIfWinningAt(self, loc):
        r, c = loc
        return self.checkSeq(loc, # horizontal
                             [(r-i, c) for i in range(1, 5)], 
                             [(r+i, c) for i in range(1, 5)]) >= 5 \
            or self.checkSeq(loc, # vertical
                             [(r, c-i) for i in range(1, 5)],
                             [(r, c+i) for i in range(1, 5)]) >= 5\
            or self.checkSeq(loc, # upperleft-lowerright
                             [(r-i, c-i) for i in range(1, 5)],
                             [(r+i, c+i) for i in range(1, 5)]) >= 5\
            or self.checkSeq(loc, # upperright-lowerleft
                             [(r+i, c-i) for i in range(1, 5)],
                             [(r-i, c+i) for i in range(1, 5)]) >= 5


    def validLoc(self, loc):
        """ Takes in a coordinate and returns if that coord is within valid range.
        """
        r, c = loc
        return 0 <= r and r < SIZEOFBOARD and 0 <= c and c < SIZEOFBOARD
    

    def checkSeq(self, loc, side1, side2):
        """ Takes in a coordinate and two sequences of coordinates.
        The two sequences should both be consecutive, starting from a position one unit away from
            loc, and end at a position five units away.
        The positions in the two sequences should form a straight line, just as what one would
            check for victory in gomoku.
        Returns the number of consecutive chess pieces including the center piece.
        """
        r, c = loc
        chess = self.grid[r][c]
        count = 1
        for side in [side1, side2]:
            for check in side:
                if not self.validLoc(check):
                    break
                r, c = check
                if self.grid[r][c] is not chess:
                    break
                count += 1
        return count
    

def main():
    game = Game()
    if DEBUG:
        printGame(game)
    p = character.BLACK
    while True:
        r, c = [int(elem) for elem in input().split()]
        res = game.down(p, (r, c))
        if DEBUG:
            print()
            printGame(game)
        if res == 1:
            print("WIN for {}".format("BLACK" if p is character.BLACK else "WHITE"))
            input()
            return
        if res > 1:
            print("bad:", res)
        else:
            p = character.BLACK if p == character.WHITE else character.WHITE


def printGame(game):
    print(" ", " ".join([str(elem) for elem in range(SIZEOFBOARD)]))
    for r in range(SIZEOFBOARD):
        print(r, end=" ")
        for c in range(SIZEOFBOARD):
            if game.grid[r][c] is character.BLACK:
                print("*", end=" ")
            elif game.grid[r][c] is character.WHITE:
                print("#", end=" ")
            else:
                print(" ", end=" ")
        print()


if __name__ == "__main__":
    SIZEOFBOARD = 5
    DEBUG = 1
    main()