"""xnxx 101 oyun məntiqi (2, 3 və 4 nəfər)."""
import random

rng = random.SystemRandom()
ALL = [(a, b) for a in range(7) for b in range(a, 7)]
ORDER = [1, 2, 3, 4, 5, 6, 0]        # ilk qoşa sırası: 1-1, 2-2, 3-3 ...
WIN = 101
norm = lambda t: (min(t), max(t))
pips = lambda ts: sum(a + b for a, b in ts)


class Game:
    def __init__(self, n):
        if n not in (2, 3, 4):
            raise ValueError("n 2, 3 və ya 4 olmalıdır")
        self.n = n
        self.score = [0] * (2 if n == 4 else n)   # 4 nəfərdə komanda xalı
        self.round = 0
        self.over = False
        self.mid = 0
        self.msg = None
        self.start_round(None)

    def key(self, s):
        return s % 2 if self.n == 4 else s

    def _say(self, **kw):
        self.mid += 1
        self.msg = dict(kw, id=self.mid)

    # ---------- YENİ: əl yoxlaması ----------
    def _hand_ok(self, hand):
        """Bir oyunçunun əlindəki daşlar üçün yoxlama.

        True = OK (oyana bilər), False = yenidən qarışdır lazımdır.

        Qaydalar (hər rəqəm 0-6 üçün ayrı-ayrı):
        - ≤ 4 dənə → OK
        - 5 dənə + qoşa (x-x) əlindədirsə → OK
        - 5 dənə + qoşa yoxdursa → yenidən qarışdır
        - 6, 7 dənə → yenidən qarışdır
        - Ümumi qoşa sayı 5+ → yenidən qarışdır
        """
        digit_count = {d: 0 for d in range(7)}
        for a, b in hand:
            digit_count[a] += 1
            if b != a:
                digit_count[b] += 1

        # Hər rəqəm üçün ayrı-ayrı yoxla
        for d in range(7):
            cnt = digit_count[d]
            if cnt >= 6:                              # 6, 7 dənə → yenidən
                return False
            if cnt == 5 and (d, d) not in hand:       # 5 dənə, qoşa yoxdur → yenidən
                return False

        # Ümumi qoşa sayı 5+ → yenidən qarışdır
        doubles = sum(1 for a, b in hand if a == b)
        if doubles >= 5:
            return False

        return True

    def _deal(self):
        """Daşları qarışdır və paylaş. Əllər uyğun deyilsə yenidən qarışdır.

        max_attempts = 500 — kifayət qədər yüksəkdir, praktikada
        uyğun əl çox tez tapılır (adətən ilk 5-10 cəhddə).
        """
        max_attempts = 500
        hands = market = None
        for _ in range(max_attempts):
            tiles = ALL[:]
            rng.shuffle(tiles)
            hands = [sorted(tiles[i * 7:(i + 1) * 7]) for i in range(self.n)]
            market = tiles[self.n * 7:]
            # Bütün oyunçuların əllərini yoxla
            if all(self._hand_ok(h) for h in hands):
                return hands, market
        # 500 cəhddən sonra da uyğun gəlmədisə — sonuncunu qəbul et
        # (praktikada bu hal baş vermir, amma sonsuz dövr qorunması)
        return hands, market

    # ---------- RAUND BAŞLAT ----------
    def start_round(self, starter):
        self.hands, self.market = self._deal()
        self.board, self.passes, self.result, self.must = [], 0, None, None
        self.nleft = 0                 # soldan əlavə olunan daş sayı (zəncirin başlanğıc daşı)
        self.round += 1

        if starter is None:
            # İlk əl: ən kiçik qoşa ilə başlanır
            for d in ORDER:
                for s, h in enumerate(self.hands):
                    if (d, d) in h:
                        self.turn, self.must = s, (d, d)
                        break
                if self.must:
                    break
            if not self.must:
                # Heç kimdə qoşa yoxdursa — ən böyük daş
                b = max((a + c, max(a, c), s, (a, c))
                        for s, h in enumerate(self.hands) for a, c in h)
                self.turn, self.must = b[2], b[3]
        else:
            self.turn = starter % self.n

        self._say(seat=self.turn, kind="start")
        self._settle()

    def ends(self):
        return (self.board[0][0], self.board[-1][1]) if self.board else None

    def playable(self, s):
        if s < 0:
            return []
        if not self.board:
            return [self.must] if self.must else list(self.hands[s])
        L, R = self.ends()
        return [t for t in self.hands[s] if L in t or R in t]

    def can_draw(self, s):
        if s < 0 or not self.board or s != self.turn or self.result:
            return False
        return (self.n == 2 and len(self.market) >= 4) or (self.n == 3 and len(self.market) >= 2)

    def _settle(self):
        """Gedişi olmayan və bazara gedə bilməyən oyunçu avtomatik pas keçir."""
        safety = 0
        while not self.result:
            safety += 1
            if safety > self.n * 4 + 10:      # sonsuz dövr qorunması
                return self._end(True)
            s = self.turn
            if self.playable(s) or self.can_draw(s):
                return
            self.passes += 1
            self._say(seat=s, kind="pass")
            if self.passes >= self.n:
                return self._end(True)
            self.turn = (s + 1) % self.n

    def play(self, seat, tile, side):
        if self.result or seat != self.turn:
            return "Növbə sizdə deyil"
        try:
            t = norm(tuple(tile))
        except (TypeError, ValueError):
            return "Yanlış daş formatı"
        if t not in self.hands[seat]:
            return "Belə daş yoxdur"
        if not self.board:
            if self.must and t != self.must:
                return f"Oyuna {self.must[0]}-{self.must[1]} daşı ilə başlanmalıdır"
            self.board.append(t)
        else:
            L, R = self.ends()
            a, b = t
            if side == "L" and L in t:
                self.board.insert(0, (a, b) if b == L else (b, a))
                self.nleft += 1
            elif side == "R" and R in t:
                self.board.append((a, b) if a == R else (b, a))
            else:
                return "Bu daş ora uyğun gəlmir"
        self.hands[seat].remove(t)
        self.passes, self.must = 0, None
        self._say(seat=seat, kind="play", tile=list(t))
        if not self.hands[seat]:
            self._end(False)
            return None
        self.turn = (seat + 1) % self.n
        self._settle()
        return None

    def draw(self, seat):
        if not self.can_draw(seat):
            return "Bazardan daş çəkmək olmaz"
        k = 2 if self.n == 2 else 1
        for _ in range(k):
            self.hands[seat].append(self.market.pop())
        self.hands[seat].sort()
        self._say(seat=seat, kind="draw", k=k)
        self._settle()
        return None

    def _end(self, blocked):
        w = min(range(self.n), key=lambda s: pips(self.hands[s])) if blocked else self.turn
        pts = sum(pips(self.hands[s]) for s in range(self.n) if self.key(s) != self.key(w))
        self.score[self.key(w)] += pts
        if max(self.score) >= WIN:
            self.over = True
        self.result = {"winner": w, "blocked": blocked, "points": pts,
                       "hands": [list(h) for h in self.hands]}
        self._say(seat=w, kind="end")

    def next_round(self):
        if self.result and not self.over:
            self.start_round(self.result["winner"])

    def view(self, seat):
        mine = seat >= 0 and self.turn == seat and not self.result
        return {
            "n": self.n, "hand": self.hands[seat] if seat >= 0 else [],
            "counts": [len(h) for h in self.hands],
            "board": self.board, "origin": self.nleft, "ends": self.ends(), "turn": self.turn,
            "market": len(self.market), "score": self.score, "round": self.round,
            "can_draw": self.can_draw(seat), "playable": self.playable(seat) if mine else [],
            "must": self.must, "msg": self.msg, "result": self.result,
            "over": self.over, "win": WIN,
        }
