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
                    "role": assigned,
                    "name": p.name,
                })
            othersDict[player.name] = role
        ret[p] = json.dumps(
            {
                "action": "Self Join",
                "gameID": self.ID,
                "name": p.name,
                "role": assigned,
                "others": othersDict,
                "board": self.game.grid,
                "next": 3 - self.game.last,
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
            if res == 1:
                self.ended = True
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
        role: gomoku.character = self.players.pop(p, None)
        for player in self.players.keys():
            ret[player] = json.dumps(
                {
                    "action": "Another Leave",
                    "role": role,
                    "name": p.name,
                })
        ret[p] = json.dumps({"action": "Self Leave"})
        return ret


    def nextRole(self) -> gomoku.character:
        b = False
        w = False
        for role in self.players.values():
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

    def __init__(self, retryThreshold=10, gameIDLen=32):
        self.logger = logging.getLogger("Server")
        self.retryThreshold = retryThreshold
        self.gameIDLen = gameIDLen
        self.sessions: Dict[str, GameSession] = dict()
        self.sessionsLock: asyncio.Lock = asyncio.Lock()
        self.connectionID = 0
        # self.players: Dict[str, Player] = dict()
        # self.playersLock: asyncio.Lock = asyncio.Lock()


    async def dispatcher(self, websocket: websockets.server.WebSocketServerProtocol, path: str):
        conn: int = self.connectionID
        self.connectionID += 1
        player: Player = None
        try:
            self.logger.info(f"new connection from websocket: {websocket}, assigning connectionID {conn}, path={path}")
            player = Player(websocket)
            player.conn = conn
            while True:

                clientMsg: str = await websocket.recv()
                self.logger.info(f"new message from {conn}, string is \"{clientMsg}\"")
                try:
                    req: Dict = json.loads(clientMsg)
                except:
                    self.logger.warning(f"bad request from {conn}: cannot load json")
                    await websocket.send(error("Bad request: json error"))
                    continue

                action: str = req.get("action", None)

                if action == "Join":
                    if player.game is not None:
                        self.logger.warning(f"bad request from {conn}: joining while already in game")
                        await websocket.send(error("Invalid action: already in game"))
                        continue

                    ID: str = req.get("ID", None)
                    gameSession = await self.join(ID, player)

                    name: str = req.get("name", None)
                    if name is None:
                        name = f"some random guy {conn}"
                    player.name = name

                    if gameSession is None:
                        # cannot put the player in a game
                        self.logger.warning(f"server error for {conn}: could not put the player into a game")
                        await websocket.send(error("Cannot join game"))
                        continue

                    async with gameSession.lock:
                        messages = gameSession.addPlayer(player)
                    for target, message in messages.items():
                        self.logger.info(f"sending: {target.conn}, {message}")
                        await target.ws.send(message)

                elif action == "Put":
                    if player.game is None:
                        # player isn't in a game
                        self.logger.warning(f"invalid action from {conn}: not in a game when trying to put")
                        await websocket.send(error("Invalid action: not in game"))
                        continue

                    loc: Tuple[int, int] = req.get("location", None)
                    if loc is None:
                        # bad request
                        self.logger.warning(f"bad request from {conn}: does not have location specified")
                        await websocket.send(error("Bad request: no location specified"))
                        continue

                    async with player.game.lock:
                        messages = player.game.put(player, loc)
                    for target, message in messages.items():
                        self.logger.info(f"sending: {target.conn}, {message}")
                        await target.ws.send(message)
                    
                else:
                    self.logger.warning(f"bad request from {conn}: unsupported action")
                    await websocket.send(error("Bad request: invalid action"))

        except(websockets.exceptions.ConnectionClosed,
            websockets.exceptions.ConnectionClosedOK,
            websockets.exceptions.ConnectionClosedError):
            info = f"client {conn} closes"
            if player is None or player.game is None:
                # The player is not in a game
                self.logger.info(info + ", client not in game")
                return
            self.logger.info(info + ", dropping client out")

            gameSession = player.game
            async with gameSession.lock:
                messages = gameSession.delPlayer(player)
            for target, message in messages.items():
                if target == player:
                    continue
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
                return self.sessions[ID]
        
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


    def getRandomGameID(self) -> str:
        return str(random.getrandbits(self.gameIDLen))


def error(msg: str):
    return json.dumps({"action": "Error", "reason": msg})


def main():
    logging.basicConfig(level=logging.INFO)
    server = Server()
    asyncio.get_event_loop().run_until_complete(websockets.serve(server.dispatcher, "localhost", 8080))
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
