var ws;
const EMPTY = 0, BLACK = 1, WHITE = 2, SIZE = 15;
const wsuri = "ws://localhost:8080";

function init() {
    // Connection
    ws = new WebSocket(wsuri);
    ws.onmessage = process;

    window.role = EMPTY;

    base = document.getElementById("base");
    crossWidth = Math.floor(50 / SIZE);
    for (let i = 0; i < SIZE; i++) {
        let row = document.createElement("div");
        row.classList.add("row");
        row.classList.add("no-gutters");
        for (let j = 0; j < SIZE; j++) {
            let cross = document.createElement("img");
            cross.classList.add("img-fluid");
            cross.id = i*SIZE + j;
            cross.onclick = putDown;
            suffix = "n.jpg";
            if (i == 0) {
                if (j == 0) {
                    cross.src = "ul" + suffix;
                } else if (j == SIZE - 1) {
                    cross.src = "ur" + suffix;
                } else {
                    cross.src = "up" + suffix;
                }
            } else if (i == SIZE - 1) {
                if (j == 0) {
                    cross.src = "ll" + suffix;
                } else if (j == SIZE - 1) {
                    cross.src = "lr" + suffix;
                } else {
                    cross.src = "lo" + suffix;
                }
            } else {
                if (j == 0) {
                    cross.src = "le" + suffix;
                } else if (j == SIZE - 1) {
                    cross.src = "ri" + suffix;
                } else {
                    cross.src = "ce" + suffix;
                }
            }
            let col = document.createElement("div");
            col.classList.add("col");
            col.append(cross);
            row.append(col);
        }
        base.append(row);
    }

    document.getElementById("chatInput").addEventListener("keyup", ifReturn(chat));
    document.getElementById("gameID").addEventListener("keyup", ifReturn(join));
    document.getElementById("playerName").addEventListener("keyup", ifReturn(join));

    document.getElementById("chatBox").value = "Chat:\n";
}

function process(msg) {
    console.log("receive:", msg.data);
    let resp = JSON.parse(msg.data);
    window.resp = resp;
    let action = resp["action"];
    if (action == "Error") { ///////////////////////////////////////
        console.log(resp["reason"]);

    } else if (action == "Self Join") { ////////////////////////////
        // show gameID
        document.getElementById("gameID").value = resp["gameID"];
        document.getElementById("gameID").readOnly = true;

        // add self
        let role = resp["role"];
        window.role = role;
        addPlayerAs(resp["name"], role);
        document.getElementById("playerName").value = resp["name"];
        document.getElementById("playerName").readOnly = true;

        // render board
        for (let row in resp["board"]) {
            let r = resp["board"][row];
            for (let col in r) {
                changeSlotTo(parseInt(row) * SIZE + parseInt(col), r[col]);
            }
        }

        // add others
        let others = resp["others"];
        // window.others = others;
        for (let name in others) {
            addPlayerAs(name, others[name]);
        }

        // next player note
        let next = resp["next"];
        if (resp["ended"] == true) {
            document.getElementById("messageBar").innerText = ["", "Black", "White"][next] + " has won!";
        } else {
            document.getElementById("messageBar").innerText = ["", "Black", "White"][next] + " is moving...";
        }

        // disable the Join Button
        document.getElementById("joinButton").onclick = leave;
        document.getElementById("joinButton").innerText = "Leave";

    } else if (action == "Self Leave") {////////////////////////////
        window.role = EMPTY;

        // clear board
        for (let i = 0; i < SIZE; i++) {
            for (let j = 0; j < SIZE; j++) {
                changeSlotTo(i * SIZE + j, 0);
            }
        }

        document.getElementById("messageBar").innerText = "You have left the game.";

        document.getElementById("blkPlayerItem").firstElementChild.innerText = "BLACK: ";
        document.getElementById("whtPlayerItem").firstElementChild.innerText = "WHITE: ";

        let specList = document.getElementById("spectatorList");
        while (specList.childElementCount > 1) {
            specList.removeChild(specList.lastChild);
        }

        document.getElementById("gameID").readOnly = false;
        document.getElementById("playerName").readOnly = false;

        document.getElementById("joinButton").onclick = join;
        document.getElementById("joinButton").innerText = "Join!";

        document.getElementById("chatBox").value = "Chat:\n";

    } else if (action == "Putted") { ///////////////////////////////
        let ID = parseInt(resp["location"][0]) * SIZE + parseInt(resp["location"][1]);
        let role = resp["role"];
        changeSlotTo(ID, role);

        let lbl = document.getElementById("messageBar");
        if (resp["winning"] == 0) {
            lbl.innerText = ["", "White", "Black"][role] + " is moving...";
        } else if (resp["winning"] == 1) {
            lbl.innerText = ["", "Black", "White"][role] + " has won!";
        }

    } else if (action == "Another Join") {
        let otherRole = resp["role"];
        let otherName = resp["name"];
        addPlayerAs(otherName, otherRole);

    } else if (action == "Another Leave") {
        let otherRole = resp["role"];
        let otherName = resp["name"];
        if (otherRole == null) {
            return;
        } else if (otherRole == 1 || otherRole == 2) {
            let id = ["", "blkPlayerItem", "whtPlayerItem"][otherRole];

            let lbl = document.getElementById(id).firstElementChild;
            lbl.innerText = lbl.innerText.substring(0, 7);
        } else {
            let specList = document.getElementById("spectatorList");
            for (child of specList.children) {
                if (child.innerText == otherName && child != specList.firstElementChild) {
                    specList.removeChild(child);
                    break;
                }
            }
        }
    } else if (action == "Chat") {
        let chatBox = document.getElementById("chatBox");
        chatBox.value += resp["from"] + ": " + resp["content"] + "\n";
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

init();


function changeSlotTo(id, role) {
    img = document.getElementById(String(id));
    img.src = img.src.replace(/.\.jpg/, ["n", "b", "w"][role]+".jpg");
}


function addPlayerAs(name, role) {
    if (role == BLACK) {
        document.getElementById("blkPlayerItem").firstElementChild.innerText = "BLACK: " + name;
    } else if (role == WHITE) {
        document.getElementById("whtPlayerItem").firstElementChild.innerText = "WHITE: " + name;
    } else {
        let li = document.createElement("li");
        li.classList.add("list-group-item");
        li.innerText = name;
        document.getElementById("spectatorList").appendChild(li);
    }
}

function ifReturn(callable) {
    return function(e) {
        if (e.keyCode == 13) {
            callable();
        }
    }
}


function join() {
    ws.send(JSON.stringify({
            "action": "Join",
            "ID": document.getElementById("gameID").value,
            "name": document.getElementById("playerName").value,
        }));
}

function leave() {
    ws.send(JSON.stringify({
        "action": "Leave",
    }));
}

function putDown(e) {
    if (window.role == EMPTY) {
        return;
    }
    let img = e.target;
    let id = parseInt(img.id);
    if (img.src.indexOf("n.jpg") == -1) {
        return;
    }
    ws.send(JSON.stringify({
        "action": "Put",
        "location": [Math.floor(id/SIZE), id%SIZE],
    }));
}

function chat() {
    ws.send(JSON.stringify({
        "action": "Chat",
        "message": document.getElementById("chatInput").value,
    }));
    document.getElementById("chatInput").value = "";
}