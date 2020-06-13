#!/usr/bin/env python3
import asyncio, json, random
import websockets
import gomoku 

MAXGAMEIDBITS = 64
RETRYTHRESHOLD = 10
games = dict()

class Session():
    def __init__(self, sessionID, game):
        self.ID = sessionID
        self.game = game
        self.white = None
        self.black = None
        self.spectators = []

    def addPlayer(self, player: str) -> int:
        if self.black is None:
            self.black = player
            return 1
        elif self.white is None:
            self.white = player
            return 2
        else:
            self.spectators.append(player)
            return 0

def join(ID: str, name: str):
    """
    Joins in a game with the provided ID. If it doesn't exist, create one.
    Returns the session, and the player's character
    """
    if ID is not None and ID not in games.keys():
        # The user specified a valid empty sessionID
        s = Session(ID, gomoku.Game())
        games[ID] = s

    retries = 0
    while ID is None:
        # The user didn't specify a session ID
        ID = random.getrandbits(MAXGAMEIDBITS)
        if ID not in games.keys():
            s = Session(ID, gomoku.Game())
            games[ID] = s
            break
        ID = None
        retries += 1
        if retries > RETRYTHRESHOLD:
            return None, None
    
    # Either way, we add the player into the game.
    s = games[ID]
    p = s.addPlayer(name)
    return s, p
    

def formulateGame(session):
    ret = dict()
    ret["ID"] = session.ID
    ret["grid"] = session.game.grid
    ret["next"] = session.game.next
    return ret


async def dispatcher(websocket: websockets.server.WebSocketServerProtocol, path):
    """
    Called when a new connection establishes. Handles the connection in a infinite loop wrapped
    in a try-except block. When connection breaks, the except clause will catch it and process
    it gracefully.
    """
    try:
        while True:
            msg = await websocket.recv()
            print("Received a message")

            try:
                req = json.loads(msg)
            except:
                print("Bad request")
                return await websocket.send("bad request")

            action: str = req.get("action", None)

            if action == "Join":
                print("Received request to join game")
                ID, name = req.get("ID", None), req.get("name", None)

                session, character = join(ID, name)
                if session is None:
                    assert ID is not None
                    print("Could not establish a new game session, retry limit exceeded. (Shouldn't usually happen!)")
                    return await websocket.send("game is too full")

                await websocket.send(json.dumps(
                    {
                        "ID": session.ID,
                        "grid": session.game.grid,
                        "next": session.game.next,
                        "color": character
                    }))
            elif action == "Down":
                pass
                ID = req.get("ID", None)
                p = req.get("player", None)
                loc = req.get("location", None)
                if ID is None or ID not in games.keys() or p is None or loc is None:
                    print("bad")
                    await websocket.send("bad")
                    return
                res = games[ID].down(ID, p, loc)
                
            else:
                print("Bad request")
                return await websocket.send("bad request")
    except (websockets.exceptions.ConnectionClosed,
            websockets.exceptions.ConnectionClosedOK,
            websockets.exceptions.ConnectionClosedError):
        print("client closes")
    except:
        print("other errors")



def main():
    asyncio.get_event_loop().run_until_complete(websockets.serve(dispatcher, "localhost", 8080))
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
