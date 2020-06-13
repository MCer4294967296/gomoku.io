### Flow:
1. Billy goes to the website. Enters in Billy and a valid (probably empty) session ID.
    1. Server gets a new connection.
    1. Server receives a message wanting to join a game, along with the name Billy
    1. Server initiates a session with sessionID
    1. Server puts Billy onto the black spot of the game
    1. Server returns to the browser the sessionID, which color is played, and the gameState
1. Billy got dropped into a game session.
    1. Browser renders the gameState, shows the sessionID as well.
    1. If Billy chooses to put down a piece, He can do that because on the server, game is ready.
1. Billy shares that ID with Chris.
    1. Maybe via a global chat?
1. Chris enters in Chris and that ID.
    1. Server gets a new connection.
    1. Server receives a message
    1. Server finds that session
    1. Server puts Chris onto the white spot
    1. Server returns to the browser the sessionID, which color is played, and the gameState
1. Chris enters the same session.
    1. Browser renders.
1. They play.

### Message formats:
1. The request to join a game:
```
Request: {
    "action": "Join",
    "ID": optional string, // Session ID
    "name": optional string, // Player name
}
Response: {
    "ID": integer, // Session ID
    "grid": List of Lists of integers, // game grid
    "next": integer, // the color to move next
    "color": integer, // the player's color
}
```

### gameState:
1. The grid
2. The next player