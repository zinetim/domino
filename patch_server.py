import re

# ---------------- game.py: bazardan daşı oyunçu seçir ----------------
g = open('game.py', encoding='utf-8').read()
if 'picks' not in g:
    new_draw = '''    def draw(self, seat, picks=None):
        if not self.can_draw(seat):
            return "Bazardan daş çəkmək olmaz"
        k = 2 if self.n == 2 else 1
        if picks is None:
            idx = list(range(len(self.market) - k, len(self.market)))
        else:
            try:
                idx = sorted({int(i) for i in picks})
            except (TypeError, ValueError):
                return "Yanlış seçim"
            if len(idx) != k or idx[0] < 0 or idx[-1] >= len(self.market):
                return f"Bazardan {k} daş seçin"
        for i in reversed(idx):
            self.hands[seat].append(self.market.pop(i))
        self.hands[seat].sort()
        self._say(seat=seat, kind="draw", k=k)
        self._settle()
        return None
'''
    g2, n = re.subn(r'    def draw\(self, seat\):.*?(?=\n    def _end)', lambda m: new_draw, g, count=1, flags=re.S)
    assert n == 1, "game.py: draw tapılmadı"
    open('game.py', 'w', encoding='utf-8').write(g2)
    print("game.py OK")
else:
    print("game.py: artıq tətbiq olunub")

# ---------------- app.py: draw(picks) + /ice ----------------
a = open('app.py', encoding='utf-8').read()
if 'picks' not in a:
    a2, n = re.subn(r'@sio\.on\("draw"\)\ndef draw\(_=None\):.*?(?=\n\n\n@sio\.on\("next"\))',
                    lambda m: '''@sio.on("draw")
def draw(d=None):
    r, seat, _u = ctx()
    if not r:
        return
    picks = d.get("picks") if isinstance(d, dict) else None
    err = r["game"].draw(seat, picks)
    emit("err", err) if err else push(r)''', a, count=1, flags=re.S)
    assert n == 1, "app.py: draw handler tapılmadı"
    a = a2
if '/ice' not in a:
    anchor = '@app.route("/healthz")\ndef health():\n    return "ok"\n'
    assert anchor in a, "app.py: healthz tapılmadı"
    ice = anchor + '''

ICE_CACHE = {"t": 0, "v": None}


def ice_servers():
    """WebRTC üçün STUN/TURN siyahısı. Uzaq məsafədə səs üçün TURN lazımdır.
    Render-də METERED_DOMAIN (məs. domino.metered.live) və METERED_API_KEY təyin edin."""
    now = time.time()
    if ICE_CACHE["v"] and now - ICE_CACHE["t"] < 300:
        return ICE_CACHE["v"]
    stun = [{"urls": "stun:stun.l.google.com:19302"}, {"urls": "stun:stun1.l.google.com:19302"}]
    dom = os.environ.get("METERED_DOMAIN", "").strip().replace("https://", "").strip("/")
    key = os.environ.get("METERED_API_KEY", "").strip()
    turn = os.environ.get("TURN_URLS", "").strip()
    servers = None
    try:
        if dom and key:
            import requests
            rr = requests.get(f"https://{dom}/api/v1/turn/credentials", params={"apiKey": key}, timeout=6)
            rr.raise_for_status()
            data = rr.json()
            if isinstance(data, list) and data:
                servers = data
        elif turn:
            servers = stun + [{"urls": [u.strip() for u in turn.split(",") if u.strip()],
                               "username": os.environ.get("TURN_USERNAME", ""),
                               "credential": os.environ.get("TURN_CREDENTIAL", "")}]
    except Exception:
        servers = None
    if not servers:
        servers = stun + [{"urls": ["turn:openrelay.metered.ca:80", "turn:openrelay.metered.ca:443",
                                    "turn:openrelay.metered.ca:443?transport=tcp"],
                           "username": "openrelayproject", "credential": "openrelayproject"}]
    else:
        ICE_CACHE.update(t=now, v=servers)
    return servers


@app.route("/ice")
def ice():
    r = jsonify(iceServers=ice_servers())
    r.headers["Cache-Control"] = "no-store"
    return r
'''
    a = a.replace(anchor, ice, 1)
open('app.py', 'w', encoding='utf-8').write(a)
print("app.py OK")
