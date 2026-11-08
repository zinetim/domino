import os
import random
import time
import secrets
import string

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit

from game import Game

app = Flask(__name__)
sio = SocketIO(
    app,
    async_mode="eventlet",   # eventlet tövsiyə olunur
    cors_allowed_origins="*",
    ping_interval=20,
    ping_timeout=40,
)
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

rooms = {}       # kod -> otaq
users = {}       # sid -> istifadəçi
user_room = {}   # uid -> kod
spec_room = {}   # sid -> kod (izləyicilər)
last_react = {}  # sid -> son reaksiya vaxtı


# ---------- HTTP ----------
@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/config")
def config():
    return jsonify(google=CLIENT_ID)


@app.route("/healthz")
def health():
    return "ok"


# ---------- KÖMƏKÇİLƏR ----------
def payload(r, i):
    g = r["game"]
    return {
        "code": r["code"],
        "n": r["n"],
        "seat": i,
        "spec": i < 0,
        "watchers": len(r.get("specs", {})),
        "players": [{"name": p["name"], "pic": p["pic"]} for p in r["players"]],
        "voice": sorted(r.get("voice", set())),
        "game": g.view(i) if g else None,
    }


def push(r):
    for i, sid in enumerate(r["sids"]):
        if sid:
            sio.emit("state", payload(r, i), to=sid)
    for sid in list(r.get("specs", {})):
        sio.emit("state", payload(r, -1), to=sid)


def me():
    u = users.get(request.sid)
    if not u:
        emit("err", "Əvvəlcə daxil olun")
    return u


def my_room(u):
    """(room, seat) qaytarır; tapılmasa (None, None)."""
    if not u:
        return None, None
    r = rooms.get(user_room.get(u["uid"]))
    if not r:
        return None, None
    seat = next(
        (i for i, p in enumerate(r["players"]) if p["uid"] == u["uid"]),
        None,
    )
    if seat is None:
        return None, None
    return r, seat


def close_specs(r):
    for sid in list(r.get("specs", {})):
        sio.emit("closed", "Otaq bağlandı", to=sid)
        spec_room.pop(sid, None)
    r["specs"] = {}


# ---------- GİRİŞ ----------
@sio.on("auth")
def auth(d):
    if d.get("credential"):
        try:
            from google.auth.transport import requests as greq
            from google.oauth2 import id_token
            info = id_token.verify_oauth2_token(
                d["credential"], greq.Request(), CLIENT_ID
            )
            user = {
                "uid": "G" + info["sub"],
                "pic": info.get("picture", ""),
                "name": (info.get("given_name") or info.get("name") or "Oyunçu")[:16],
            }
        except Exception:
            return emit("autherr", "Google girişi alınmadı")
    else:
        name = (d.get("name") or "Qonaq").strip()[:16] or "Qonaq"
        gid = "".join(
            c for c in str(d.get("gid") or secrets.token_hex(6)) if c.isalnum()
        )[:24]
        user = {"uid": "g" + gid, "name": name, "pic": ""}

    users[request.sid] = user
    emit("authed", user)

    r, seat = my_room(user)
    if r and seat is not None:
        r["sids"][seat] = request.sid
        push(r)


# ---------- OTAQ ----------
@sio.on("create")
def create(d):
    u = me()
    if not u:
        return
    try:
        n = int(d.get("n", 2))
    except (TypeError, ValueError):
        return
    if n not in (2, 3, 4):
        return
    leave(None)
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    while code in rooms:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    r = {
        "code": code,
        "n": n,
        "players": [u],
        "sids": [request.sid],
        "game": None,
    }
    rooms[code] = r
    user_room[u["uid"]] = code
    push(r)


@sio.on("join")
def join(d):
    u = me()
    if not u:
        return
    code = str(d.get("code", "")).upper().strip()
    r = rooms.get(code)
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
def leave(_=None):
    u = users.get(request.sid)
    if not u:
        return

    # İzləyici idisə
    code = spec_room.pop(request.sid, None)
    if code is not None:
        if code in rooms:
            rooms[code].get("specs", {}).pop(request.sid, None)
            push(rooms[code])
        return emit("left")

    r, seat = my_room(u)
    if not r or seat is None:
        return

    if r["game"]:  # oyun başlayıbsa, otaq bağlanır
        for i, sid in enumerate(r["sids"]):
            if sid and i != seat:
                sio.emit("closed", f"{u['name']} oyundan çıxdı", to=sid)
            user_room.pop(r["players"][i]["uid"], None)
        close_specs(r)
        rooms.pop(r["code"], None)
    else:
        r["players"].pop(seat)
        r["sids"].pop(seat)
        user_room.pop(u["uid"], None)
        if not r["players"]:
            close_specs(r)
            rooms.pop(r["code"], None)
        else:
            push(r)
    emit("left")


# ---------- OYUN ----------
@sio.on("play")
def play(d):
    u = me()
    if not u:
        return
    r, seat = my_room(u)
    if not r or not r["game"] or seat is None:
        return
    err = r["game"].play(seat, d.get("tile", [0, 0]), d.get("side", "R"))
    if err:
        emit("err", err)
    else:
        push(r)


@sio.on("draw")
def draw(_=None):
    u = me()
    if not u:
        return
    r, seat = my_room(u)
    if not r or not r["game"] or seat is None:
        return
    err = r["game"].draw(seat)
    if err:
        emit("err", err)
    else:
        push(r)


@sio.on("next")
def nxt(_=None):
    u = me()
    if not u:
        return
    r, _s = my_room(u)
    if r and r["game"]:
        r["game"].next_round()
        push(r)


@sio.on("rematch")
def rematch(_=None):
    u = me()
    if not u:
        return
    r, _s = my_room(u)
    if r and r["game"] and r["game"].over:
        r["game"] = Game(r["n"])
        push(r)


# ---------- İZLƏMƏ ----------
@sio.on("spectate")
def spectate(d):
    u = me()
    if not u:
        return
    code = str(d.get("code", "")).upper().strip()
    r = rooms.get(code)
    if not r:
        return emit("err", "Otaq tapılmadı")
    mr, _s = my_room(u)
    if mr is r:
        return push(r)
    leave(None)
    r.setdefault("specs", {})[request.sid] = u
    spec_room[request.sid] = r["code"]
    push(r)


@sio.on("enter")
def enter(d):
    u = me()
    if not u:
        return
    code = str(d.get("code", "")).upper().strip()
    r = rooms.get(code)
    if not r:
        return emit("err", "Otaq tapılmadı")
    mr, _s = my_room(u)
    if mr is r:
        return push(r)
    if not r["game"] and len(r["players"]) < r["n"]:
        join(d)
    else:
        spectate(d)


@sio.on("rooms")
def rooms_list(_=None):
    if not me():
        return
    out = []
    for r in rooms.values():
        g = r["game"]
        out.append(
            {
                "code": r["code"],
                "n": r["n"],
                "names": [p["name"] for p in r["players"]],
                "playing": bool(g),
                "round": g.round if g else 0,
                "score": g.score if g else [],
                "over": bool(g and g.over),
                "watchers": len(r.get("specs", {})),
            }
        )
    out.sort(key=lambda x: (not x["playing"], x["code"]))
    emit("rooms", out[:30])


# ---------- REAKSİYA ----------
@sio.on("react")
def react(d):
    u = me()
    if not u:
        return
    r, seat = my_room(u)
    k = d.get("k")
    if not r or not r["game"] or seat is None:
        return
    if not isinstance(k, int) or not (0 <= k < 5):
        return
    now = time.time()
    if now - last_react.get(request.sid, 0) < 1.2:
        return
    last_react[request.sid] = now
    for sid in r["sids"]:
        if sid:
            sio.emit("react", {"seat": seat, "k": k}, to=sid)


# ---------- SƏS (WebRTC signal) ----------
@sio.on("voice")
def voice(d):
    u = me()
    if not u:
        return
    r, seat = my_room(u)
    if not r or seat is None:
        return
    v = r.setdefault("voice", set())
    if d.get("on"):
        others = sorted(v - {seat})
        v.add(seat)
        emit("voicepeers", others)
    else:
        v.discard(seat)
    push(r)


@sio.on("rtc")
def rtc(d):
    u = me()
    if not u:
        return
    r, seat = my_room(u)
    to = d.get("to")
    if (
        r
        and isinstance(to, int)
        and 0 <= to < len(r["sids"])
        and r["sids"][to]
        and seat is not None
    ):
        sio.emit("rtc", {"from": seat, "data": d.get("data")}, to=r["sids"][to])


# ---------- AYRILMA ----------
@sio.on("disconnect")
def disc():
    last_react.pop(request.sid, None)

    # İzləyici idisə
    code = spec_room.pop(request.sid, None)
    if code in rooms:
        rooms[code].get("specs", {}).pop(request.sid, None)
        push(rooms[code])

    u = users.pop(request.sid, None)
    if not u:
        return
    r, seat = my_room(u)
    if r and seat is not None and r["sids"][seat] == request.sid:
        r["sids"][seat] = None
        r.get("voice", set()).discard(seat)
        push(r)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    sio.run(
        app,
        host="0.0.0.0",
        port=port,
        allow_unsafe_werkzeug=True,
    )
