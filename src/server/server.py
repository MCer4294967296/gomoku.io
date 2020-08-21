#!/usr/bin/env python3
import asyncio, json, logging, random
from enum import Enum
from typing import List, Dict, Tuple

import websockets

import gomoku


class Player:
    class State(Enum):
        INIT=0
        INGAME=1

    def __init__(self, ws):
        self.ws = ws
        self.id = -1
        self.state = Player.State.INIT
        #######################################################################
        # self.game: GameSession = GameSession("")
        self.game: GameSession = None
        #######################################################################
        self.name: str = ""


class GameSession:

    def __init__(self, ID: str):
        self.ID = ID
        self.game: gomoku.Game = gomoku.Game()
        self.ended: bool = False
        self.players: Dict[Player, gomoku.character] = dict()
        self.lock: asyncio.Lock = asyncio.Lock()
    

    def addPlayer(self, p: Player, char: gomoku.character = None) -> Dict[Player, str]:
        if char is None:
            char = self.nextRole()
        if p in self.players:
            raise # this player should already be in the game. Even if disconnected, it should be handled.

        if char is gomoku.character.EMPTY or char in self.players.values():
            # either the player chooses to be an observer,
            # or the character is already chosen,
            # assign the player the role of observer
            assigned = gomoku.character.EMPTY
        else:
            assigned = char

        ret: Dict[Player, str] = dict()
        othersDict: Dict[str, str] = dict()
        for player, role in self.players.items():
            ret[player] = json.dumps(
                {
                    "action": "Another Join",
                    "role": assigned.name,
                    "name": p.name,
                })
            othersDict[player.name] = role.name
        ret[p] = json.dumps(
            {
                # "action": "Self Join",
                # "role": assigned.name,
                "others": othersDict,
                # "board": self.game.grid
            })
        self.players[p] = assigned
        p.game = self
        return ret


    def put(self, p: Player, loc: Tuple[int, int]) -> Dict[Player, str]:
        if self.ended:
            return {p: error("Invalid action: Game has ended")}
        role: gomoku.character = self.players.get(p, None)
        res = self.game.down(role, loc)
        ret: Dict[Player, str] = dict()
        if res == 0 or res == 1:
            # successful
            # we need to inform everyone that the specified role has just put down a piece
            info = json.dumps(
                {
                    "action": "Putted",
                    "location": loc,
                    "role": role,
                    "winning": res == 1,
                })
            for player in self.players.keys():
                ret[player] = info
        else:
            err = "Invalid action"
            if res == 2 or res == 3:
                err += ": illegal position"
            elif res == 4 or res == 5:
                err += ": illegal player"
            else:
                err += ": other rules"
            ret[p] = error(err)
        return ret


    def delPlayer(self, p: Player) -> Dict[Player, str]:
        ret: Dict[Player, str] = dict()
        self.players.pop(p, None)
        for player in self.players.keys():
            ret[player] = json.dumps(
                {
                    "action": "Another Leave",
                    "name": p.name,
                })
        ret[p] = json.dumps({"action": "Self Leave"})
        return ret


    def nextRole(self) -> gomoku.character:
        b = False
        w = False
        for role in self.players.items():
            if role is gomoku.character.BLACK:
                b = True
            elif role is gomoku.character.WHITE:
                w = True
        if not b:
            return gomoku.character.BLACK
        if not w:
            return gomoku.character.WHITE
        return gomoku.character.EMPTY


class Server:

    def __init__(self, logLevel=logging.DEBUG, retryThreshold=10, gameIDLen=20):
        self.logger = logging.Logger("gomoku.io", level=logLevel)
        self.retryThreshold = retryThreshold
        self.gameIDLen = gameIDLen
        self.sessions: Dict[str, GameSession] = dict()
        self.sessionsLock: asyncio.Lock = asyncio.Lock()
        # self.players: Dict[str, Player] = dict()
        # self.playersLock: asyncio.Lock = asyncio.Lock()


    async def dispatcher(self, websocket: websockets.server.WebSocketServerProtocol, path: str):
        player: Player = None
        try:
            self.logger.debug(f"new connection, path={path}")
            player = Player(websocket)
            while True:
                clientMsg: str = await websocket.recv()
                self.logger.debug(f"new message from websocket: {websocket}")
                try:
                    req: Dict = json.loads(clientMsg)
                except:
                    self.logger.warning("bad request: cannot load json")
                    await websocket.send(error("Bad request: json error"))
                    continue

                action: str = req.get("action", None)

                if action == "Join":
                    ID: str = req.get("ID", None)
                    gameSession = await self.join(ID, player)
                    if gameSession is None:
                        # cannot put the player in a game
                        self.logger.warning(f"server error: could not put the player into a game")
                        await websocket.send(error("Cannot join game"))
                        continue
                    async with gameSession.lock:
                        messages = gameSession.addPlayer(player)
                    for target, msg in messages.items():
                        await target.ws.send(msg)

                elif action == "Put":
                    if player.game is None:
                        # player isn't in a game
                        self.logger.warning(f"invalid action: not in a game when trying to put")
                        await websocket.send(error("Invalid action: not in game"))
                        continue
                    loc: Tuple[int, int] = req.get("location", None)
                    if loc is None:
                        # bad request
                        self.logger.warning(f"bad request: does not have location specified")
                        await websocket.send(error("Bad request: no location specified"))
                        continue
                    async with player.game.lock:
                        messages = player.game.put(player, loc)
                    for target, message in messages.item():
                        await target.ws.send(message)
                    
                else:
                    self.logger.warning("bad request: unsupported action")
                    await websocket.send(error("Bad request: invalid action"))

        except(websockets.exceptions.ConnectionClosed,
            websockets.exceptions.ConnectionClosedOK,
            websockets.exceptions.ConnectionClosedError):
            info = "client closes"
            if player is None or player.game is None:
                # The player is not in a game
                self.logger.info(info + ", client not in game")
                return
            gameSession = player.game
            async with gameSession.lock:
                messages = gameSession.delPlayer(player)
            for target, message in messages.item():
                await target.ws.send(message)

            player.game = None
            if len(gameSession.players) == 0:
                async with self.sessionsLock:
                    self.sessions.pop(gameSession.ID)

        # except Exception as e:
        #     self.logger.error("other exceptions: " + str(e))


    async def join(self, ID: str, player: Player) -> GameSession:
        if ID is not None:
            async with self.sessionsLock:
                if ID not in self.sessions.keys():
                    s = GameSession(ID)
                    self.sessions[ID] = s
            return s
        
        retries = 0
        while ID is None and retries <= self.retryThreshold:
            ID = self.getRandomGameID()
            async with self.sessionsLock:
                if ID not in self.sessions.keys():
                    s = GameSession(ID)
                    self.sessions[ID] = s
                    return s
            ID = None
            retries += 1
        return None


    def getRandomGameID(self):
        return random.getrandbits(self.gameIDLen)


def error(msg: str):
    return json.dumps({"action": "Error", "reason": msg})


def main():
    server = Server()
    asyncio.get_event_loop().run_until_complete(websockets.serve(server.dispatcher, "localhost", 8080))
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
    debug = True
