import os
import random
import secrets
import string

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

from game import Game

app = Flask(__name__)
sio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

rooms = {}       # kod -> otaq
users = {}       # sid -> istifadəçi
user_room = {}   # uid -> kod


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/config")
def config():
    return jsonify(google=CLIENT_ID)


@app.route("/healthz")
def health():
    return "ok"


def payload(r, i):
    g = r["game"]
    return {"code": r["code"], "n": r["n"], "seat": i,
            "players": [{"name": p["name"], "pic": p["pic"]} for p in r["players"]],
            "game": g.view(i) if g else None}


def push(r):
    for i, sid in enumerate(r["sids"]):
        if sid:
            sio.emit("state", payload(r, i), to=sid)


def me():
    u = users.get(request.sid)
    if not u:
        emit("err", "Əvvəlcə daxil olun")
    return u


def my_room(u):
    r = rooms.get(user_room.get(u["uid"]))
    if not r:
        return None, None
    return r, next(i for i, p in enumerate(r["players"]) if p["uid"] == u["uid"])


@sio.on("auth")
def auth(d):
    if d.get("credential"):
        try:
            from google.auth.transport import requests as greq
            from google.oauth2 import id_token
            info = id_token.verify_oauth2_token(d["credential"], greq.Request(), CLIENT_ID)
            user = {"uid": "G" + info["sub"], "pic": info.get("picture", ""),
                    "name": (info.get("given_name") or info.get("name") or "Oyunçu")[:16]}
        except Exception:
            return emit("autherr", "Google girişi alınmadı")
    else:
        name = (d.get("name") or "Qonaq").strip()[:16] or "Qonaq"
        gid = "".join(c for c in str(d.get("gid") or secrets.token_hex(6)) if c.isalnum())[:24]
        user = {"uid": "g" + gid, "name": name, "pic": ""}
    users[request.sid] = user
    emit("authed", user)
    r, seat = my_room(user)
    if r:
        r["sids"][seat] = request.sid
        push(r)


@sio.on("create")
def create(d):
    u = me()
    if not u:
        return
    n = int(d.get("n", 2))
    if n not in (2, 3, 4):
        return
    leave(None)
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    while code in rooms:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    r = {"code": code, "n": n, "players": [u], "sids": [request.sid], "game": None}
    rooms[code] = r
    user_room[u["uid"]] = code
    push(r)


@sio.on("join")
def join(d):
    u = me()
    if not u:
        return
    r = rooms.get(str(d.get("code", "")).upper().strip())
    if not r:
        return emit("err", "Otaq tapılmadı")
    if r["game"] or len(r["players"]) >= r["n"]:
        return emit("err", "Otaq doludur")
    leave(None)
    r["players"].append(u)
    r["sids"].append(request.sid)
    user_room[u["uid"]] = r["code"]
    if len(r["players"]) == r["n"]:
        r["game"] = Game(r["n"])
    push(r)


@sio.on("leave")
def leave(_):
    u = users.get(request.sid)
    if not u:
        return
    r, seat = my_room(u)
    if not r:
        return
    if r["game"]:                      # gedən olduqda oyun bağlanır
        for i, sid in enumerate(r["sids"]):
            if sid and i != seat:
                sio.emit("closed", f"{u['name']} oyundan çıxdı", to=sid)
            user_room.pop(r["players"][i]["uid"], None)
        rooms.pop(r["code"], None)
    else:
        r["players"].pop(seat)
        r["sids"].pop(seat)
        user_room.pop(u["uid"], None)
        if not r["players"]:
            rooms.pop(r["code"], None)
        else:
            push(r)
    emit("left")


@sio.on("play")
def play(d):
    u = me()
    r, seat = my_room(u) if u else (None, None)
    if not r or not r["game"]:
        return
    err = r["game"].play(seat, d.get("tile", [0, 0]), d.get("side", "R"))
    emit("err", err) if err else push(r)


@sio.on("draw")
def draw(_):
    u = me()
    r, seat = my_room(u) if u else (None, None)
    if not r or not r["game"]:
        return
    err = r["game"].draw(seat)
    emit("err", err) if err else push(r)


@sio.on("next")
def nxt(_):
    u = me()
    r, _s = my_room(u) if u else (None, None)
    if r and r["game"]:
        r["game"].next_round()
        push(r)


@sio.on("rematch")
def rematch(_):
    u = me()
    r, _s = my_room(u) if u else (None, None)
    if r and r["game"] and r["game"].over:
        r["game"] = Game(r["n"])
        push(r)


@sio.on("disconnect")
def disc():
    u = users.pop(request.sid, None)
    if not u:
        return
    r, seat = my_room(u)
    if r and r["sids"][seat] == request.sid:
        r["sids"][seat] = None


if __name__ == "__main__":
    sio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            allow_unsafe_werkzeug=True)
