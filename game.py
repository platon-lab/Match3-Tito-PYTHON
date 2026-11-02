# -*- coding: utf-8 -*-
"""Игровой экран: поле, препятствия, особые фишки (с ограниченным запасом), таймер-бомбы,
слизь, туман и перевёрнутая гравитация."""
import math
import random

import pygame

import art
from config import (BASE_W, BASE_H, ROWS, COLS, CELL, BX, BY, GEM_R, GEMS, MONSTER_COLORS,
                    SHAPE_NAMES, MECH_NAMES, OBST_HP, write_save, make_level, goal_text)
from logic import (Star, Bomb, Magnet, Lightning, Timer, Monster, SPECIALS, is_gem, is_special,
                   find_matches, has_possible_move, swap_cells, gravity_fill, reshuffle_gems,
                   make_board)
from render import (get_font, draw_text, wrap_text, R, P, gradient, make_stars, star_field,
                    draw_portrait, ease_out, ease_in_out, lerp)
from ui import Scene, Button, Bokeh, panel, chip, chip_width
from story import RESULT_WON, RESULT_LOST

NEIGH4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
MAX_SPECIALS = 2                       # одновременно на поле
OBST_UNDER = ("brick", "stone")        # рисуются под фишкой
OBST_BLOCK = ("web", "chain", "stone") # фишка в клетке нельзя двигать, пока препятствие цело
OBST_COL = {"ice": (170, 230, 255), "web": (235, 240, 255), "brick": (200, 110, 80),
            "chain": (165, 170, 185), "stone": (150, 148, 160), "slime": (120, 235, 100)}


def _cell_to_json(v):
    if v is None:
        return None
    if is_gem(v):
        return ["g", v]
    if isinstance(v, Star):
        return ["s"]
    if isinstance(v, Bomb):
        return ["b"]
    if isinstance(v, Magnet):
        return ["mg"]
    if isinstance(v, Lightning):
        return ["ln"]
    if isinstance(v, Timer):
        return ["t", v.left]
    if isinstance(v, Monster):
        return ["m", v.species, v.hp]
    return None


def _cell_from_json(x):
    if x is None:
        return None
    tag = x[0]
    if tag == "g":
        return int(x[1])
    if tag == "s":
        return Star()
    if tag == "b":
        return Bomb()
    if tag == "mg":
        return Magnet()
    if tag == "ln":
        return Lightning()
    if tag == "t":
        return Timer(int(x[1]))
    if tag == "m":
        return Monster(int(x[1]), int(x[2]))
    return None


class GameScene(Scene):
    def __init__(self, app, n, restore=None):
        super().__init__(app)
        self.n = n
        self.cfg = make_level(n)
        self.nc = self.cfg["colors"]
        self.bg = gradient(self.cfg["top"], self.cfg["bottom"])
        self.stars_bg = make_stars(40)
        self.bokeh = Bokeh(14)
        self.fog_base = None
        self.obst = {}
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.score = 0
        self.collected = [0] * len(GEMS)
        self.kills = 0
        self.turns = 0
        self.spec_left = self.cfg["spec_budget"]
        self.moves = self.cfg.get("moves")
        self.time_left = self.cfg.get("time")
        self.obst_total = 0
        self.mon_total = 0

        ok = False
        if restore is not None:
            try:
                self._restore(restore)
                ok = True
            except Exception:
                ok = False
        if not ok:
            self._fresh()
        self.blocked = self._blocked_cells()

        self.phase = "idle"
        self.anim_t = 0.0
        self.a = None
        self.b = None
        self.swap_bad = False
        self.pending = set()
        self.pop_matches = set()
        self.pop_cells = set()
        self.pop_t = 0.0
        self.pop_dur = 0.22
        self.blast = None
        self.fall_items = []
        self.fall_dur = 0.3
        self.cascade = 0
        self.turn_flag = False
        self.last_cell = None
        self.selected = None
        self.drag = None
        self.particles = []
        self.texts = []
        self.bolts = []
        self.shake = 0.0
        self.result = None
        self.result_t = 0.0
        self.result_msg = ""
        self.paused = False
        self.card_t = 0.0 if ok else 2.8
        self.pause_btn = Button(R(452, 862, 62, 48), "II", self.pause, (60, 60, 100), 26)
        self.buttons = [self.pause_btn]
        if not ok:
            self.app.audio.play_voice(self.cfg["hint"])

    # ---------- создание поля и сохранение
    def _fresh(self):
        self.moves = self.cfg.get("moves")
        self.time_left = self.cfg.get("time")
        self.score = 0
        self.collected = [0] * len(GEMS)
        self.kills = 0
        self.turns = 0
        self.spec_left = self.cfg["spec_budget"]
        self._make_field()
        self.obst_total = len(self.obst)
        self.mon_total = self.monsters_alive()

    def _make_field(self):
        cells = [(r, c) for r in range(ROWS) for c in range(COLS)]
        while True:
            self.board = make_board(self.nc)
            random.shuffle(cells)
            k = 0
            for _ in range(self.cfg["monsters"]):
                r, c = cells[k]
                k += 1
                self.board[r][c] = Monster(random.randrange(len(MONSTER_COLORS)))
            for _ in range(self.cfg["timers"]):
                r, c = cells[k]
                k += 1
                self.board[r][c] = Timer(self.cfg["timer_len"])
            if has_possible_move(self.board):
                break
        free = cells[k:]
        self.obst = {}
        i = 0
        for kind, count in self.cfg["obst"].items():
            for _ in range(count):
                if i >= len(free):
                    break
                self.obst[free[i]] = [kind, OBST_HP[kind]]
                i += 1
        # препятствия не должны запирать игрока без ходов
        self.blocked = self._blocked_cells()
        while self.blocked and not has_possible_move(self.board, self.blocked):
            p = random.choice(list(self.blocked))
            del self.obst[p]
            self.blocked = self._blocked_cells()

    def to_dict(self):
        return {
            "n": self.n,
            "board": [[_cell_to_json(v) for v in row] for row in self.board],
            "obst": [[r, c, k, hp] for (r, c), (k, hp) in self.obst.items()],
            "obst_total": self.obst_total,
            "mon_total": self.mon_total,
            "score": self.score,
            "collected": list(self.collected),
            "kills": self.kills,
            "turns": self.turns,
            "spec_left": self.spec_left,
            "moves": self.moves,
            "time_left": self.time_left,
        }

    def _restore(self, d):
        self.board = [[_cell_from_json(x) for x in row] for row in d["board"]]
        self.obst = {(int(r), int(c)): [kind, int(hp)] for r, c, kind, hp in d["obst"]}
        self.obst_total = int(d["obst_total"])
        self.mon_total = int(d["mon_total"])
        self.score = int(d["score"])
        self.collected = [int(x) for x in d["collected"]]
        self.kills = int(d["kills"])
        self.turns = int(d["turns"])
        self.spec_left = int(d["spec_left"])
        self.moves = d["moves"]
        self.time_left = d["time_left"]

    def autosave(self):
        if self.phase != "idle" or self.result:
            return
        self.app.save["game"] = self.to_dict()
        write_save(self.app.save)

    def on_quit(self):
        try:
            self.autosave()
        except Exception:
            pass

    # ---------- состояние поля
    def monsters_alive(self):
        return sum(1 for row in self.board for v in row if isinstance(v, Monster))

    def _blocked_cells(self):
        return {p for p, (k, hp) in self.obst.items() if k in OBST_BLOCK and hp > 0}

    def _specials_on_board(self):
        return sum(1 for row in self.board for v in row if isinstance(v, SPECIALS))

    def _timer_positions(self):
        return [(r, c) for r in range(ROWS) for c in range(COLS) if isinstance(self.board[r][c], Timer)]

    def goals_met(self):
        cfg = self.cfg
        if self.score < cfg["score"]:
            return False
        for k, need in cfg["collect"].items():
            if self.collected[k] < need:
                return False
        if self.obst:
            return False
        if self.monsters_alive() > 0:
            return False
        return True

    # ---------- управление состоянием
    def pause(self):
        if self.result or self.card_t > 0 or self.paused:
            return
        self.paused = True
        self.app.audio.play("click")
        self.buttons = [
            Button(R(110, 400, 320, 66), "ПРОДОЛЖИТЬ", self.resume, (255, 150, 60)),
            Button(R(110, 486, 320, 66), "ЗАНОВО", self.restart, (70, 150, 240)),
            Button(R(110, 572, 320, 66), "В МЕНЮ", self.exit_to_menu, (150, 90, 220)),
        ]

    def resume(self):
        self.paused = False
        self.buttons = [self.pause_btn]

    def restart(self):
        self.app.save["game"] = None
        write_save(self.app.save)
        self.app.go(lambda: GameScene(self.app, self.n))

    def exit_to_menu(self):
        self.autosave()
        self.app.to_menu()

    def next_level(self):
        self.app.play_level(self.n + 1)

    def on_back(self):
        if self.result:
            self.exit_to_menu()
        elif self.paused:
            self.resume()
        else:
            self.pause()

    def set_result(self, kind, msg=""):
        self.result = kind
        self.result_t = 0.0
        self.result_msg = msg
        self.phase = "idle"
        self.selected = None
        self.drag = None
        save = self.app.save
        save["game"] = None
        if kind == "won":
            save["level"] = max(save["level"], self.n + 1)
            save["best"] = max(save.get("best", 0), self.n)
            write_save(save)
            self.app.audio.play("win")
            self.app.audio.play_voice(RESULT_WON)
            self.buttons = [
                Button(R(110, 540, 320, 64), "ДАЛЬШЕ", self.next_level, (255, 150, 60)),
                Button(R(110, 616, 320, 64), "В МЕНЮ", self.exit_to_menu, (150, 90, 220)),
            ]
        else:
            write_save(save)
            self.app.audio.play("lose")
            self.app.audio.play_voice(RESULT_LOST)
            self.buttons = [
                Button(R(110, 540, 320, 64), "ЗАНОВО", self.restart, (70, 150, 240)),
                Button(R(110, 616, 320, 64), "В МЕНЮ", self.exit_to_menu, (150, 90, 220)),
            ]

    # ---------- эффекты
    def _center(self, r, c):
        return BX + c * CELL + CELL / 2, BY + r * CELL + CELL / 2

    def _burst(self, x, y, color, n=8):
        for _ in range(n):
            ang = random.uniform(0, 6.28)
            sp = random.uniform(90, 260)
            self.particles.append({"x": x, "y": y, "vx": math.cos(ang) * sp,
                                   "vy": math.sin(ang) * sp - 120, "life": 0.6, "max": 0.6,
                                   "color": color, "size": random.uniform(3, 6)})

    def _text(self, text, x, y, color):
        self.texts.append({"text": text, "x": x, "y": y, "life": 1.0, "color": color})

    def _update_fx(self, dt):
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 900 * dt
            p["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0]
        for tx in self.texts:
            tx["y"] -= 60 * dt
            tx["life"] -= dt
        self.texts = [tx for tx in self.texts if tx["life"] > 0]
        self.shake = max(0.0, self.shake - dt * 40)
        for row in self.board:
            for v in row:
                if isinstance(v, Monster) and v.flash > 0:
                    v.flash = max(0.0, v.flash - dt)

    # ---------- ходы
    def _cell_at(self, pos):
        x, y = pos
        if BX <= x < BX + COLS * CELL and BY <= y < BY + ROWS * CELL:
            return int((y - BY) // CELL), int((x - BX) // CELL)
        return None

    def _tick_timers(self):
        """Удачный ход: таймеры тикают. Возвращает клетки взрыва (3 на 3) для тех, кто дошёл до нуля."""
        boom = set()
        for r, c in self._timer_positions():
            t = self.board[r][c]
            t.left -= 1
            if t.left <= 0:
                boom |= {(rr, cc) for rr in range(r - 1, r + 2) for cc in range(c - 1, c + 2)
                         if 0 <= rr < ROWS and 0 <= cc < COLS}
            else:
                self.app.audio.play("tick")
        return boom

    def try_swap(self, a, b):
        if self.phase != "idle" or self.result or self.paused or self.card_t > 0:
            return
        if self.moves is not None and self.moves <= 0:
            return
        if a in self.blocked or b in self.blocked:
            x, y = self._center(*a)
            self._text("Заблокировано!", x, y - 20, (255, 140, 140))
            self.shake = max(self.shake, 3.0)
            return
        swap_cells(self.board, a, b)
        matches = find_matches(self.board)
        self.a, self.b = a, b
        self.anim_t = 0.0
        self.cascade = 0
        self.phase = "swap"
        self.swap_bad = not matches
        self.app.audio.play("swap")
        self.last_cell = b
        self.selected = None
        if matches:
            boom = self._tick_timers()
            self.pending = set(matches) | boom
            self.pop_matches = set(matches)
            self.turns += 1
            self.turn_flag = True
            if self.moves is not None:
                self.moves -= 1
        else:
            self.pending = set()

    def activate_special(self, cell):
        """Тап по особой фишке. Не тратит ход и не тратит запас особых фишек."""
        r, c = cell
        v = self.board[r][c]
        target = set()
        kind, sound = "star", "bomb"
        if isinstance(v, Star):
            target = {(r, i) for i in range(COLS)} | {(i, c) for i in range(ROWS)}
        elif isinstance(v, Bomb):
            target = {(rr, cc) for rr in range(r - 1, r + 2) for cc in range(c - 1, c + 2)
                      if 0 <= rr < ROWS and 0 <= cc < COLS}
            kind, sound = "bomb", "boom"
        elif isinstance(v, Magnet):
            color = None
            for dr, dc in NEIGH4:
                rr, cc = r + dr, c + dc
                if 0 <= rr < ROWS and 0 <= cc < COLS and is_gem(self.board[rr][cc]):
                    color = self.board[rr][cc]
                    break
            if color is None:
                colors = [x for row in self.board for x in row if is_gem(x)]
                color = random.choice(colors) if colors else None
            if color is not None:
                target = {(rr, cc) for rr in range(ROWS) for cc in range(COLS)
                          if is_gem(self.board[rr][cc]) and self.board[rr][cc] == color}
            kind, sound = "magnet", "magnet"
        elif isinstance(v, Lightning):
            pool = [(rr, cc) for rr in range(ROWS) for cc in range(COLS)
                    if self.board[rr][cc] is not None and (rr, cc) != cell]
            target = set(random.sample(pool, min(6, len(pool))))
            kind, sound = "lightning", "lightning"
        target.add(cell)
        self.blast = (cell, kind)
        self.pending = target
        self.pop_matches = set()
        self.pop_cells = set(target)
        self.pop_t = 0.0
        self.pop_dur = 0.4
        self.cascade = 0
        self.phase = "pop"
        self.shake = 6.0
        self.app.audio.play(sound)
        self.selected = None
        self.drag = None

    def _finish_pop(self):
        cells = set(self.pop_cells)
        blast = self.blast
        self.blast = None
        ms = set(self.pop_matches)
        self.pop_matches = set()
        gem_match = [rc for rc in ms if is_gem(self.board[rc[0]][rc[1]])]
        gain = 0

        # таймер рядом с совпадением обезвреживается
        for r, c in self._timer_positions():
            if (r, c) not in cells and any((r + dr, c + dc) in cells for dr, dc in NEIGH4):
                cells.add((r, c))
                gain += 30
                x, y = self._center(r, c)
                self._text("Обезврежено!", x, y - 20, (150, 255, 200))
                self.app.audio.play("defuse")

        for (r, c) in cells:
            v = self.board[r][c]
            x, y = self._center(r, c)
            if is_gem(v):
                self.collected[v] += 1
                gain += 10 * max(1, self.cascade)
                self._burst(x, y, GEMS[v][0], 8)
            elif isinstance(v, Star):
                gain += 60
                self._burst(x, y, (200, 160, 255), 16)
            elif isinstance(v, Bomb):
                gain += 80
                self._burst(x, y, (255, 150, 60), 16)
            elif isinstance(v, Magnet):
                gain += 70
                self._burst(x, y, (120, 200, 255), 16)
            elif isinstance(v, Lightning):
                gain += 70
                self._burst(x, y, (255, 240, 120), 16)
            elif isinstance(v, Timer):
                self._burst(x, y, (255, 90, 60), 18)
                self.shake = max(self.shake, 6.0)
            if (r, c) in self.obst:
                entry = self.obst[(r, c)]
                entry[1] -= 1
                self._burst(x, y, OBST_COL[entry[0]], 8)
                if entry[1] <= 0:
                    del self.obst[(r, c)]
                    self._burst(x, y, (255, 255, 255), 10)

        # монстры получают урон, если рядом (или в зоне взрыва) есть совпадение
        for r in range(ROWS):
            for c in range(COLS):
                m = self.board[r][c]
                if not isinstance(m, Monster):
                    continue
                near = any((r + dr, c + dc) in cells
                           for dr, dc in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)))
                if not near:
                    continue
                m.hp -= 1
                m.flash = 0.3
                x, y = self._center(r, c)
                self._burst(x, y, (255, 255, 255), 8)
                self.shake = max(self.shake, 3.0)
                if m.hp <= 0:
                    self.board[r][c] = None
                    self.kills += 1
                    gain += 60
                    self._burst(x, y, MONSTER_COLORS[m.species % len(MONSTER_COLORS)], 22)

        # особая фишка появляется только из обычного совпадения и только в пределах запаса
        keep = None
        if (not blast and gem_match and len(ms) >= 4 and self.spec_left > 0
                and self._specials_on_board() < MAX_SPECIALS):
            if len(ms) >= 5:
                obj = Bomb() if random.random() < 0.5 else Magnet()
            else:
                obj = Star() if random.random() < 0.5 else Lightning()
            keep = (random.choice(gem_match), obj)
            self.spec_left -= 1

        for (r, c) in cells:
            if isinstance(self.board[r][c], Monster):
                continue
            self.board[r][c] = None
        if keep is not None:
            (kr, kc), obj = keep
            self.board[kr][kc] = obj

        self.score += gain
        if cells:
            cx = sum(self._center(r, c)[0] for r, c in cells) / len(cells)
            cy = sum(self._center(r, c)[1] for r, c in cells) / len(cells)
            self._text(f"+{gain}", cx, cy, (255, 230, 120))
            if self.cascade > 1:
                self._text(f"КАСКАД x{self.cascade}!", cx, cy - 40, (255, 150, 90))
        if len(cells) >= 5 or self.cascade >= 2:
            self.shake = max(self.shake, 5.0)
        self.fall_items = gravity_fill(self.board, self.nc, up=self.cfg["gravity"])
        maxd = max((abs(dst - src) for _, src, dst, _ in self.fall_items), default=1)
        self.fall_dur = 0.18 + 0.045 * maxd
        self.anim_t = 0.0
        self.pop_cells = set()
        self.phase = "fall"
        self.app.audio.play("fall")

    def _spread_slime(self):
        """Слизь расползается на соседнюю клетку с фишкой (раз в несколько ходов)."""
        slimes = [p for p, e in self.obst.items() if e[0] == "slime"]
        if not slimes or len(slimes) >= 12:
            return
        random.shuffle(slimes)
        for (r, c) in slimes:
            opts = [(r + dr, c + dc) for dr, dc in NEIGH4
                    if 0 <= r + dr < ROWS and 0 <= c + dc < COLS
                    and (r + dr, c + dc) not in self.obst and is_gem(self.board[r + dr][c + dc])]
            if opts:
                p = random.choice(opts)
                self.obst[p] = ["slime", 1]
                x, y = self._center(*p)
                self._burst(x, y, OBST_COL["slime"], 10)
                self._text("Слизь растёт!", x, y - 20, (150, 255, 120))
                self.app.audio.play("grow")
                return

    def _ensure_playable(self):
        if has_possible_move(self.board, self.blocked):
            return
        reshuffle_gems(self.board, self.nc, self.blocked)
        self._text("Перемешали!", BASE_W / 2, BY + 240, (255, 255, 255))
        while self.blocked and not has_possible_move(self.board, self.blocked):
            p = random.choice(list(self.blocked))
            del self.obst[p]
            self.blocked = self._blocked_cells()

    def _end_turn(self):
        self.cascade = 0
        self.phase = "idle"
        if self.turn_flag:
            self.turn_flag = False
            if self.cfg["slime_every"] and self.turns % self.cfg["slime_every"] == 0:
                self._spread_slime()
            if self.cfg["shuffle_every"] and self.turns % self.cfg["shuffle_every"] == 0:
                reshuffle_gems(self.board, self.nc, self._blocked_cells())
                self._text("Перемешали!", BASE_W / 2, BY + 240, (255, 255, 255))
        self.blocked = self._blocked_cells()
        if self.goals_met():
            self.set_result("won")
            return
        if self.moves is not None and self.moves <= 0:
            self.set_result("lost", "Ходы закончились!")
            return
        self._ensure_playable()
        self.autosave()

    def _update_board(self, dt):
        ph = self.phase
        if ph == "swap":
            self.anim_t += dt / 0.16
            if self.anim_t >= 1:
                self.anim_t = 0.0
                if self.swap_bad:
                    swap_cells(self.board, self.a, self.b)
                    self.phase = "back"
                    self.app.audio.play("bad")
                else:
                    self.phase = "pop"
                    self.pop_cells = set(self.pending)
                    self.pop_t = 0.0
                    self.pop_dur = 0.22
                    self.cascade += 1
                    self.app.audio.play("pop")
        elif ph == "back":
            self.anim_t += dt / 0.16
            if self.anim_t >= 1:
                self.anim_t = 0.0
                self.phase = "idle"
                self.a = self.b = None
        elif ph == "pop":
            self.pop_t += dt / self.pop_dur
            if self.pop_t >= 1:
                self._finish_pop()
        elif ph == "fall":
            self.anim_t += dt / self.fall_dur
            if self.anim_t >= 1:
                self.anim_t = 0.0
                self.fall_items = []
                self.phase = "check"
        elif ph == "check":
            matches = find_matches(self.board)
            if matches:
                self.pending = set(matches)
                self.pop_matches = set(matches)
                self.pop_cells = set(matches)
                self.pop_t = 0.0
                self.pop_dur = 0.22
                self.cascade += 1
                self.phase = "pop"
                self.app.audio.play("cascade")
            else:
                self._end_turn()

    # ---------- цикл
    def update(self, dt):
        super().update(dt)
        self._update_fx(dt)
        if self.paused:
            return
        if self.card_t > 0:
            self.card_t = max(0.0, self.card_t - dt)
            return
        if self.result:
            self.result_t += dt
            return
        if self.time_left is not None:
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left = 0
                self.set_result("lost", "Время вышло!")
                return
        self._update_board(dt)

    def on_down(self, pos):
        if super().on_down(pos):
            return True
        if self.card_t > 0:
            self.card_t = 0.0
            return True
        if self.paused or self.result or self.phase != "idle":
            return True
        cell = self._cell_at(pos)
        if cell is None:
            return True
        v = self.board[cell[0]][cell[1]]
        if is_special(v):
            self.activate_special(cell)
            return True
        self.drag = (pos, cell)
        return True

    def on_up(self, pos):
        if super().on_up(pos):
            return True
        if self.drag is None:
            return True
        (sx, sy), cell = self.drag
        self.drag = None
        dx, dy = pos[0] - sx, pos[1] - sy
        if abs(dx) < 18 and abs(dy) < 18:
            self._tap(cell)
        else:
            if abs(dx) > abs(dy):
                dr, dc = 0, (1 if dx > 0 else -1)
            else:
                dr, dc = (1 if dy > 0 else -1), 0
            tgt = (cell[0] + dr, cell[1] + dc)
            if 0 <= tgt[0] < ROWS and 0 <= tgt[1] < COLS:
                self.try_swap(cell, tgt)
            self.selected = None
        return True

    def _tap(self, cell):
        if self.selected is None:
            self.selected = cell
        elif self.selected == cell:
            self.selected = None
        elif abs(self.selected[0] - cell[0]) + abs(self.selected[1] - cell[1]) == 1:
            a = self.selected
            self.selected = None
            self.try_swap(a, cell)
        else:
            self.selected = cell

    # ---------- отрисовка
    def _bolt(self, s, x0, y0, x1, y1):
        pts = [(x0, y0)]
        for i in range(1, 4):
            f = i / 4
            pts.append((x0 + (x1 - x0) * f + random.uniform(-12, 12),
                        y0 + (y1 - y0) * f + random.uniform(-12, 12)))
        pts.append((x1, y1))
        pygame.draw.lines(s, (255, 250, 180), False, P(pts), 3)

    def _draw_board(self, s):
        ox = oy = 0.0
        if self.shake > 0:
            ox = random.uniform(-self.shake, self.shake)
            oy = random.uniform(-self.shake, self.shake)
        bx, by = BX + ox, BY + oy
        panel(s, R(bx - 12, by - 12, CELL * COLS + 24, CELL * ROWS + 24),
              fill=(14, 14, 30), border=(90, 80, 150), radius=22, width=2)
        for r in range(ROWS):
            for c in range(COLS):
                pygame.draw.rect(s, (36, 36, 64),
                                 R(bx + c * CELL + 4, by + r * CELL + 4, CELL - 8, CELL - 8),
                                 border_radius=12)
        for (r, c), (kind, hp) in self.obst.items():
            if kind in OBST_UNDER:
                art.draw_obstacle(s, kind, hp, bx + c * CELL + 4, by + r * CELL + 4, self.t)

        s.set_clip(R(bx, by, CELL * COLS, CELL * ROWS))
        if self.phase == "fall":
            e = ease_out(self.anim_t)
            for v, src, dst, c in self.fall_items:
                y = by + (lerp(src, dst, e) + 0.5) * CELL
                x = bx + c * CELL + CELL / 2
                art.draw_any(s, v, x, y, GEM_R, self.t)
        else:
            swapping = self.phase in ("swap", "back") and self.a is not None
            for r in range(ROWS):
                for c in range(COLS):
                    if swapping and (r, c) in (self.a, self.b):
                        continue
                    v = self.board[r][c]
                    if v is None:
                        continue
                    x = bx + c * CELL + CELL / 2
                    y = by + r * CELL + CELL / 2
                    rad = GEM_R + math.sin(self.t * 3 + r * 0.7 + c * 0.9) * 0.9
                    if self.phase == "pop" and (r, c) in self.pop_cells and not isinstance(v, Monster):
                        k = self.pop_t
                        rad = GEM_R * (1 - ease_out(k))
                        if k < 1:
                            pygame.draw.circle(s, (255, 255, 255), (int(x), int(y)),
                                               int(GEM_R * (1 + k * 1.2)), 3)
                    art.draw_any(s, v, x, y, rad, self.t)
            if swapping:
                e = ease_in_out(self.anim_t)
                pa = (bx + self.a[1] * CELL + CELL / 2, by + self.a[0] * CELL + CELL / 2)
                pb = (bx + self.b[1] * CELL + CELL / 2, by + self.b[0] * CELL + CELL / 2)
                va = self.board[self.a[0]][self.a[1]]
                vb = self.board[self.b[0]][self.b[1]]
                art.draw_any(s, va, lerp(pb[0], pa[0], e), lerp(pb[1], pa[1], e), GEM_R, self.t)
                art.draw_any(s, vb, lerp(pa[0], pb[0], e), lerp(pa[1], pb[1], e), GEM_R, self.t)
            if self.blast and self.phase == "pop":
                (br, bc), kind = self.blast
                cx0 = bx + bc * CELL + CELL / 2
                cy0 = by + br * CELL + CELL / 2
                if kind == "star":
                    hgt = int(CELL * 0.9 * (1 - self.pop_t))
                    if hgt > 2:
                        pygame.draw.rect(s, (235, 220, 255),
                                         R(bx, by + br * CELL + CELL / 2 - hgt / 2, CELL * COLS, hgt))
                        pygame.draw.rect(s, (235, 220, 255),
                                         R(bx + bc * CELL + CELL / 2 - hgt / 2, by, hgt, CELL * ROWS))
                elif kind == "bomb":
                    inset = 6 + int(20 * self.pop_t)
                    for rr in range(br - 1, br + 2):
                        for cc in range(bc - 1, bc + 2):
                            if 0 <= rr < ROWS and 0 <= cc < COLS:
                                pygame.draw.rect(s, (255, 170, 60),
                                                 R(bx + cc * CELL + inset, by + rr * CELL + inset,
                                                   CELL - 2 * inset, CELL - 2 * inset), border_radius=10)
                else:
                    for (tr, tc) in self.pop_cells:
                        tx = bx + tc * CELL + CELL / 2
                        ty = by + tr * CELL + CELL / 2
                        if kind == "magnet":
                            pygame.draw.line(s, (150, 220, 255), (cx0, cy0), (tx, ty), 3)
                        else:
                            self._bolt(s, cx0, cy0, tx, ty)
        s.set_clip(None)

        for (r, c), (kind, hp) in self.obst.items():
            if kind not in OBST_UNDER:
                art.draw_obstacle(s, kind, hp, bx + c * CELL + 4, by + r * CELL + 4, self.t)
        self._draw_fog(s, bx, by)
        if self.selected and self.phase == "idle":
            r, c = self.selected
            pulse = 2 + int(2 * math.sin(self.t * 8))
            pygame.draw.rect(s, (255, 255, 255),
                             R(bx + c * CELL + 2, by + r * CELL + 2, CELL - 4, CELL - 4),
                             pulse, border_radius=14)

    def _draw_fog(self, s, bx, by):
        if not self.cfg["fog"]:
            return
        if self.fog_base is None:
            self.fog_base = pygame.Surface((CELL * COLS, CELL * ROWS), pygame.SRCALPHA)
            self.fog_base.fill((6, 4, 14, 225))
        f = self.fog_base.copy()
        focus = [p for p in (self.selected, self.last_cell,
                             self.a if self.phase in ("swap", "back") else None) if p]
        for (r, c) in focus:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < ROWS and 0 <= cc < COLS:
                        pygame.draw.rect(f, (0, 0, 0, 0), R(cc * CELL, rr * CELL, CELL, CELL))
        s.blit(f, (int(bx), int(by)))

    def _chips(self):
        out = []
        if self.moves is not None:
            out.append((f"ХОДЫ: {self.moves}", (120, 200, 255)))
        else:
            mm, ss = int(self.time_left) // 60, int(self.time_left) % 60
            out.append((f"ВРЕМЯ {mm}:{ss:02d}", (255, 120, 120) if self.time_left < 10 else (255, 200, 120)))
        out.append((f"ОЧКИ {self.score}/{self.cfg['score']}", (255, 210, 90)))
        for k, need in self.cfg["collect"].items():
            out.append((f"{SHAPE_NAMES[k]} {min(self.collected[k], need)}/{need}", GEMS[k][0]))
        if self.obst_total or self.obst:
            out.append((f"ПРЕПЯТСТВИЯ {len(self.obst)}", (150, 220, 255)))
        if self.mon_total:
            out.append((f"МОНСТРЫ {self.monsters_alive()}/{self.mon_total}", MONSTER_COLORS[0]))
        timers = len(self._timer_positions())
        if timers:
            out.append((f"БОМБЫ {timers}", (255, 110, 90)))
        out.append((f"ОСОБЫЕ {self.spec_left}", (255, 190, 255)))
        return out

    def _draw_hud(self, s):
        panel(s, R(14, 12, 512, 240), fill=(12, 10, 30), border=(110, 90, 200), radius=24, width=2)
        draw_portrait(s, 470, 140, 100, self.t)
        draw_text(s, f"УРОВЕНЬ {self.n}", get_font(22, True), (255, 210, 90), 30, 24)
        if self.cfg["hard"]:
            w = get_font(22, True).size(f"УРОВЕНЬ {self.n}")[0]
            chip(s, 30 + w + 14, 22, "ТЯЖЁЛЫЙ", (255, 90, 90), dot=False)
        draw_text(s, self.cfg["name"], get_font(34, True), (255, 255, 255), 30, 52)
        x, y = 30, 96
        for text, col in self._chips():
            w = chip_width(text)
            if x + w > 418:
                x = 30
                y += 36
            chip(s, x, y, text, col)
            x += w + 8

    def _draw_card(self, s):
        if self.card_t <= 0:
            return
        el = 2.8 - self.card_t
        if el < 0.4:
            off = (1 - ease_out(el / 0.4)) * -260
        elif self.card_t < 0.4:
            off = ease_out((0.4 - self.card_t) / 0.4) * -260
        else:
            off = 0
        rect = R(40, 290 + off, 460, 300)
        panel(s, rect, fill=(14, 12, 34), border=(255, 205, 80), radius=24, width=3)
        cx = 270
        draw_text(s, f"УРОВЕНЬ {self.n}", get_font(26, True), (255, 205, 80), cx, rect.y + 22, "midtop")
        draw_text(s, self.cfg["name"], get_font(38, True), (255, 255, 255), cx, rect.y + 52, "midtop")
        y = rect.y + 106
        for line in wrap_text(goal_text(self.cfg), get_font(22), 410)[:3]:
            draw_text(s, line, get_font(22), (230, 230, 255), cx, y, "midtop")
            y += 28
        mech = [MECH_NAMES[m] for m in self.cfg["mech"] if m in MECH_NAMES]
        if mech:
            y += 8
            for line in wrap_text("Механики: " + ", ".join(mech), get_font(19, True), 420)[:2]:
                draw_text(s, line, get_font(19, True), (150, 220, 255), cx, y, "midtop")
                y += 24
        if self.cfg["hard"]:
            draw_text(s, "ТЯЖЁЛЫЙ УРОВЕНЬ! Будь внимателен", get_font(20, True), (255, 110, 110),
                      cx, rect.bottom - 50, "midbottom")
        draw_text(s, self.cfg["hint"], get_font(19), (170, 240, 200), cx, rect.bottom - 22, "midbottom")

    def _draw_result(self, s):
        if not self.result:
            return
        k = ease_out(min(1.0, self.result_t / 0.35))
        w, h = int(440 * k), int(420 * k)
        if w < 4:
            return
        panel_rect = R(270 - w / 2, 470 - h / 2, w, h)
        border = (255, 205, 80) if self.result == "won" else (235, 90, 90)
        pygame.draw.rect(s, (20, 16, 40), panel_rect, border_radius=24)
        pygame.draw.rect(s, border, panel_rect, 3, border_radius=24)
        if self.result_t < 0.25:
            return
        if self.result == "won":
            draw_text(s, f"УРОВЕНЬ {self.n} ПРОЙДЕН!", get_font(30, True), (255, 205, 80), 270, 300, "center")
            body = RESULT_WON
        else:
            draw_text(s, "НЕ ПОЛУЧИЛОСЬ", get_font(34, True), (240, 110, 110), 270, 300, "center")
            body = self.result_msg + " Тито не сдаётся!"
        draw_text(s, f"Очки: {self.score}", get_font(26, True), (255, 255, 255), 270, 352, "center")
        y = 400
        for line in wrap_text(body, get_font(24), 380)[:3]:
            draw_text(s, line, get_font(24), (230, 230, 255), 270, y, "center")
            y += 30

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        star_field(s, self.stars_bg, self.t)
        self.bokeh.draw(s)
        self._draw_hud(s)
        self._draw_board(s)
        hint_y = BY + CELL * ROWS + 30
        for i, line in enumerate(wrap_text("Подсказка: " + self.cfg["hint"], get_font(19), 440)[:2]):
            draw_text(s, line, get_font(19), (225, 225, 245), 270, hint_y + i * 24, "center")
        draw_text(s, "Тап по особой фишке — активировать", get_font(18), (180, 180, 210),
                  270, 880, "center")
        for p in self.particles:
            rad = max(1, int(p["size"] * (p["life"] / p["max"])))
            pygame.draw.circle(s, p["color"], (int(p["x"]), int(p["y"])), rad)
        for tx in self.texts:
            draw_text(s, tx["text"], get_font(28, True), tx["color"], tx["x"], tx["y"], "center")
        if self.paused:
            dim = pygame.Surface((BASE_W, BASE_H))
            dim.fill((0, 0, 0))
            dim.set_alpha(150)
            s.blit(dim, (0, 0))
            draw_text(s, "ПАУЗА", get_font(64, True), (255, 255, 255), 270, 300, "center")
        self._draw_card(s)
        self._draw_result(s)
        for b in self.buttons:
            b.draw(s)

