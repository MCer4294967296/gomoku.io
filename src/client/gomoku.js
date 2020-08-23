var ws = new WebSocket("ws://localhost:8080");

const EMPTY = 0, BLACK = 1, WHITE = 2, SIZE = 15;
window.role = EMPTY;

base = document.getElementById("base")
crossWidth = Math.floor(50 / SIZE);
for (let i = 0; i < SIZE; i++) {
    let row = document.createElement("div")
    row.classList.add("row");
    row.classList.add("no-gutters");
    // row.style.marginLeft = "-20px";
    // row.style.marginRight = "-20px";
    for (let j = 0; j < SIZE; j++) {
        let cross = document.createElement("img");
        cross.classList.add("img-fluid")
        cross.id = i*SIZE + j;
        cross.onclick = putDown;
        // cross.style.width = crossWidth + "vw";
        // cross.style.height = crossWidth + "vh";
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
        col.classList.add("col")
        col.append(cross);
        row.append(col);
    }
    base.append(row);
}


function process(msg) {
    console.log("receive:", msg.data);
    let resp = JSON.parse(msg.data);
    window.resp = resp;
    let action = resp["action"]
    if (action == "Error") { ///////////////////////////////////////
        console.log(resp["reason"]);

    } else if (action == "Self Join") { ////////////////////////////
        // show gameID
        document.getElementById("gameID").value = resp["gameID"];
        document.getElementById("gameID").disabled = true;

        // add self
        let role = resp["role"];
        window.role = role;
        addPlayerAs(resp["name"], role)
        document.getElementById("playerName").value = resp["name"];
        document.getElementById("playerName").disabled = true;

        // render board
        for (let row in resp["board"]) {
            let r = resp["board"][row]
            for (let col in r) {
                changeSlotTo(parseInt(row) * SIZE + parseInt(col), numToChar(r[col]));
            }
        }

        // add others
        let others = resp["others"];
        window.others = others;
        for (let name in others) {
            addPlayerAs(name, others[name]);
        }

    } else if (action == "Putted") { ///////////////////////////////
        let ID = parseInt(resp["location"][0]) * SIZE + parseInt(resp["location"][1]);

        changeSlotTo(ID, numToChar(resp["role"]))
        if (resp["winning"] == 1) {
            let lbl = document.getElementById("winning");
            lbl.innerText = ["", "Black", "White"][resp["role"]] + " has won!"
            // win;
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
    }
}
ws.onmessage = process;


function changeSlotTo(id, role) {
    img = document.getElementById(String(id));
    img.src = img.src.replace(/.\.jpg/, role+".jpg")
}


function numToChar(num, full=false) {
    let res = ["n", "b", "w"];
    return res[num];
}

function addPlayerAs(name, role) {
    if (role == BLACK) {
        document.getElementById("blkPlayerItem").firstElementChild.innerText += " " + name;
    } else if (role == WHITE) {
        document.getElementById("whtPlayerItem").firstElementChild.innerText += " " + name;
    } else {
        let li = document.createElement("li");
        li.classList.add("list-group-item");
        li.innerText = name;
        document.getElementById("spectatorList").appendChild(li);
    }
}


function connect() {
    let gameID = document.getElementById("gameID").value;
    if (gameID == "") {
        gameID = null;
    }
    let playerName = document.getElementById("playerName").value;
    if (playerName == "") {
        playerName = null;
    }
    ws.send(JSON.stringify(
        {
            "action": "Join",
            "ID": gameID,
            "name": playerName,
        }
    ));
    // function s() {
    //     console.log("sending: ", gameID, " ", playerName);
    //     ws.send(JSON.stringify(
    //         {
    //             "action": "Join",
    //             "ID": gameID,
    //             "name": playerName,
    //         }
    //     ));
    // }
    // if (ws.readyState != 1) {
    //     ws = new WebSocket("ws://localhost:8080");
    //     ws.onmessage = process;
    //     ws.onopen = s;
    // } else {
    //     s();
    // }
    
}


function putDown(e) {
    if (window.role == EMPTY) {
        return;
    }
    let img = e.target;
    let id = parseInt(img.id)
    if (img.src.indexOf("n.jpg") == -1) {
        return;
    }
    ws.send(JSON.stringify({
        "action": "Put",
        "location": [Math.floor(id/SIZE), id%SIZE],
    }));
    return;
}