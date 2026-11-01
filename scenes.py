# -*- coding: utf-8 -*-
"""Экраны: вступление, меню, настройки, дебаг-меню, игра."""
import math
import random

import pygame

from config import (BASE_W, BASE_H, ROWS, COLS, CELL, BX, BY, GEM_R, GEMS, MONSTER_COLORS,
                    SHAPE_NAMES, INTRO_LINES, INTRO_LENGTH, write_save, make_level, goal_text)
from logic import (Star, Monster, find_matches, has_possible_move, make_board,
                   swap_cells, gravity_fill, reshuffle_gems, is_gem)
from render import (get_font, draw_text, wrap_text, R, P, gradient, make_stars, star_field,
                    glow, draw_gem, draw_piece, draw_tito, draw_bone, draw_chip, chip_width,
                    make_ice_surf, draw_portrait, ease_out, ease_in_out, lerp)

NAME_COLORS = {"TITO": (255, 205, 80), "MUR": (200, 150, 255), "NAR": (130, 225, 255)}
NAME_TITLES = {"TITO": "Тито", "MUR": "Мурзик", "NAR": "Рассказчик"}
GROUND = 560
HOUSES = [(10, 330, 120, (170, 120, 100)), (140, 300, 110, (150, 110, 120)),
          (260, 350, 130, (120, 140, 170)), (400, 320, 130, (180, 140, 110))]


class Scene:
    def __init__(self, app):
        self.app = app
        self.buttons = []
        self.mouse = (0, 0)
        self.t = 0.0
        self._pressed = None

    def update(self, dt):
        self.t += dt
        for b in self.buttons:
            b.update(dt, self.mouse)

    def draw(self, s):
        for b in self.buttons:
            b.draw(s)

    def on_motion(self, pos):
        self.mouse = pos

    def on_down(self, pos):
        self.mouse = pos
        for b in self.buttons:
            if b.enabled and b.rect.collidepoint(pos):
                b.pressed = True
                self._pressed = b
                return True
        return False

    def on_up(self, pos):
        b = self._pressed
        self._pressed = None
        if b is not None:
            b.pressed = False
            if b.rect.collidepoint(pos):
                self.app.audio.play("click")
                b.cb()
                return True
        return False

    def on_back(self):
        pass


class Button:
    def __init__(self, rect, text, cb, color=(70, 130, 230), font_size=34):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.cb = cb
        self.color = color
        self.font_size = font_size
        self.hover = 0.0
        self.press = 0.0
        self.pressed = False
        self.enabled = True

    def update(self, dt, mouse):
        target = 1.0 if self.rect.collidepoint(mouse) else 0.0
        self.hover += (target - self.hover) * min(1.0, dt * 12)
        tp = 1.0 if self.pressed else 0.0
        self.press += (tp - self.press) * min(1.0, dt * 20)

    def draw(self, s):
        k = 1 + 0.04 * self.hover - 0.06 * self.press
        r = pygame.Rect(0, 0, int(self.rect.w * k), int(self.rect.h * k))
        r.center = self.rect.center
        dark = tuple(int(c * 0.55) for c in self.color)
        light = tuple(min(255, int(c * 1.25 + 30)) for c in self.color)
        pygame.draw.rect(s, dark, r.move(0, 6), border_radius=20)
        pygame.draw.rect(s, self.color, r, border_radius=20)
        pygame.draw.rect(s, light, R(r.x + 8, r.y + 6, r.w - 16, max(6, r.h // 3)), border_radius=14)
        if self.text:
            draw_text(s, self.text, get_font(self.font_size, True), (255, 255, 255),
                      r.centerx, r.centery, "center")


# ============================================================ МЕНЮ
class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = gradient((40, 20, 75), (6, 6, 18))
        self.stars = make_stars(70)
        self.floaters = [self._floater(True) for _ in range(16)]
        self.buttons = [
            Button(R(90, 560, 360, 66), "ИГРАТЬ", self.play, (255, 150, 60)),
            Button(R(90, 646, 360, 66), "НАСТРОЙКИ", self.settings, (60, 170, 140)),
            Button(R(90, 732, 360, 66), "ВЫХОД", self.quit_game, (200, 70, 80)),
        ]

    def _floater(self, anywhere=False):
        return {"x": random.uniform(0, BASE_W),
                "y": random.uniform(0, BASE_H) if anywhere else BASE_H + 40,
                "kind": random.randrange(len(GEMS)), "vy": random.uniform(20, 50),
                "r": random.uniform(10, 20), "ph": random.uniform(0, 6.28)}

    def update(self, dt):
        super().update(dt)
        for i, f in enumerate(self.floaters):
            f["y"] -= f["vy"] * dt
            if f["y"] < -40:
                self.floaters[i] = self._floater()

    def on_down(self, pos):
        if super().on_down(pos):
            return True
        if pygame.Rect(150, 280, 240, 240).collidepoint(pos):
            self.app.tito_taps += 1
            if self.app.tito_taps >= 30:
                self.app.tito_taps = 0
                self.app.go(lambda: DebugScene(self.app))
        return True

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        star_field(s, self.stars, self.t)
        for f in self.floaters:
            pulse = 1 + 0.08 * math.sin(self.t * 2 + f["ph"])
            draw_gem(s, f["kind"], f["x"], f["y"], f["r"] * pulse)
        bob = math.sin(self.t * 2) * 5
        draw_text(s, "ТИТО", get_font(120, True), (80, 40, 0), 274, 124 + bob, "center")
        draw_text(s, "ТИТО", get_font(120, True), (255, 200, 60), 270, 120 + bob, "center")
        draw_text(s, "ТРИ В РЯД", get_font(46, True), (110, 230, 255), 270, 192, "center")
        draw_text(s, f"Уровень {self.app.save['level']}", get_font(24), (220, 220, 240), 270, 232, "center")
        draw_portrait(s, 270, 520 + math.sin(self.t * 3) * 4, 250, self.t,
                      blink=(self.t % 4) < 0.12)
        for b in self.buttons:
            b.draw(s)

    def play(self):
        self.app.play_level(self.app.save["level"])

    def settings(self):
        self.app.go(lambda: SettingsScene(self.app))

    def quit_game(self):
        self.app.running = False


class SettingsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = gradient((20, 40, 40), (5, 10, 15))
        self.buttons = [
            Button(R(90, 300, 360, 70), "", self.toggle_sound, (60, 160, 130), 30),
            Button(R(90, 390, 360, 70), "", self.toggle_voice, (70, 130, 200), 30),
            Button(R(120, 840, 300, 64), "НАЗАД", self.back, (90, 90, 120), 30),
        ]

    def update(self, dt):
        super().update(dt)
        self.buttons[0].text = "ЗВУКИ: " + ("ВКЛ" if self.app.save["sound"] else "ВЫКЛ")
        self.buttons[1].text = "ОЗВУЧКА: " + ("ВКЛ" if self.app.save["voice"] else "ВЫКЛ")

    def toggle_sound(self):
        self.app.save["sound"] = not self.app.save["sound"]
        write_save(self.app.save)

    def toggle_voice(self):
        self.app.save["voice"] = not self.app.save["voice"]
        write_save(self.app.save)

    def back(self):
        self.app.to_menu()

    def on_back(self):
        self.back()

    def voice_text(self):
        st = self.app.voice_status
        state = st["state"]
        if state in ("idle", "loading"):
            return f"Озвучка скачивается: {st['done']} из {st['total']}"
        if state == "done":
            return "Озвучка готова"
        if state == "offline":
            return "Нет интернета: озвучка не скачана"
        if state == "nogtts":
            return "Нет модуля gTTS: голоса не будет"
        return "Нет доступа к папке для озвучки"

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        draw_text(s, "НАСТРОЙКИ", get_font(52, True), (255, 255, 255), 270, 150, "center")
        draw_text(s, self.voice_text(), get_font(20), (190, 230, 210), 270, 230, "center")
        super().draw(s)


# ============================================================ ДЕБАГ-МЕНЮ
class DebugScene(Scene):
    STAR_VALUES = [0, 1, 2, 3, 5, 8]

    def __init__(self, app):
        super().__init__(app)
        self.n = app.save["level"]
        self.bg = gradient((30, 10, 40), (5, 5, 12))
        self.buttons = [
            Button(R(30, 190, 100, 62), "-10", lambda: self._add(-10), (150, 80, 80), 26),
            Button(R(140, 190, 100, 62), "-1", lambda: self._add(-1), (150, 80, 80), 26),
            Button(R(300, 190, 100, 62), "+1", lambda: self._add(1), (80, 150, 90), 26),
            Button(R(410, 190, 100, 62), "+10", lambda: self._add(10), (80, 150, 90), 26),
            Button(R(90, 280, 360, 62), "ИГРАТЬ С ЭТОГО УРОВНЯ", self.play, (255, 150, 60), 24),
            Button(R(90, 356, 360, 62), "БОСС-БОЙ", self.boss, (200, 70, 120), 26),
            Button(R(90, 432, 360, 62), "", self.toggle_inf, (70, 150, 240), 24),
            Button(R(90, 508, 360, 62), "", self.cycle_stars, (60, 170, 140), 24),
            Button(R(90, 584, 360, 62), "ПОКАЗАТЬ ЗАСТАВКУ", self.intro, (150, 90, 220), 24),
            Button(R(90, 660, 360, 62), "СБРОСИТЬ ПРОГРЕСС", self.reset, (190, 70, 70), 24),
            Button(R(120, 850, 300, 62), "НАЗАД", self.back, (90, 90, 120), 30),
        ]

    def _add(self, d):
        self.n = max(1, self.n + d)

    def play(self):
        self.app.save["level"] = self.n
        write_save(self.app.save)
        self.app.play_level(self.n)

    def boss(self):
        boss_n = max(100, ((self.n + 99) // 100) * 100)
        self.app.play_boss(boss_n)

    def toggle_inf(self):
        self.app.save["inf_moves"] = not self.app.save["inf_moves"]
        write_save(self.app.save)

    def cycle_stars(self):
        cur = self.app.save["start_stars"]
        idx = self.STAR_VALUES.index(cur) if cur in self.STAR_VALUES else -1
        self.app.save["start_stars"] = self.STAR_VALUES[(idx + 1) % len(self.STAR_VALUES)]
        write_save(self.app.save)

    def intro(self):
        self.app.go(lambda: IntroScene(self.app, lambda: self.app.to_menu()))

    def reset(self):
        self.app.save["level"] = 1
        self.app.save["best"] = 0
        write_save(self.app.save)
        self.n = 1

    def back(self):
        self.app.to_menu()

    def on_back(self):
        self.back()

    def update(self, dt):
        super().update(dt)
        s = self.app.save
        self.buttons[6].text = "БЕСК. ХОДЫ: " + ("ВКЛ" if s["inf_moves"] else "ВЫКЛ")
        self.buttons[7].text = f"ЗВЁЗДЫ НА СТАРТЕ: {s['start_stars']}"

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        draw_text(s, "ДЕБАГ-МЕНЮ", get_font(44, True), (255, 120, 200), 270, 90, "center")
        draw_text(s, f"Уровень: {self.n}", get_font(40, True), (255, 255, 255), 270, 235, "center")
        draw_text(s, f"Прогресс сейчас: {self.app.save['level']}", get_font(20),
                  (200, 200, 220), 270, 150, "center")
        super().draw(s)


# ============================================================ ВСТУПЛЕНИЕ
class IntroScene(Scene):
    """Сцена, где всё что говорят — то и происходит: Тито роняет рюкзак."""

    def __init__(self, app, on_done):
        super().__init__(app)
        self.on_done = on_done
        self.sky = gradient((90, 160, 235), (210, 235, 255))
        self.rng = random.Random(7)
        self.tt = 0.0
        self.tito_x = -120.0
        self.dirn = 1
        self.walk = 0.0
        self.torn = False
        self.items = []
        self.shake = 0.0
        self.line_i = -1
        self.chars = 0.0
        self.typing = False
        self.speaker = "NAR"
        self.text = ""
        self.buttons = [Button(R(372, 24, 144, 46), "Пропустить", self.finish, (60, 60, 90), 22)]

    def _spill(self):
        """Рюкзак рвётся: гаснут самоцветы и косточка, падают на дорогу."""
        x0 = self.tito_x - 30
        y0 = GROUND - 150
        for v in [self.rng.randrange(len(GEMS)) for _ in range(6)] + ["bone"]:
            self.items.append({"v": v, "x": x0 + self.rng.uniform(-14, 14), "y": y0,
                               "vx": self.rng.uniform(-170, -50), "vy": self.rng.uniform(-430, -240),
                               "rest": False})

    def _physics(self, dt):
        floor = GROUND - 8
        for it in self.items:
            if it["rest"]:
                continue
            it["vy"] += 900 * dt
            it["x"] += it["vx"] * dt
            it["y"] += it["vy"] * dt
            if it["y"] >= floor:
                it["y"] = floor
                if abs(it["vy"]) < 90:
                    it["rest"] = True
                    it["vy"] = 0
                    it["vx"] = 0
                else:
                    it["vy"] = -it["vy"] * 0.4
                    it["vx"] *= 0.6

    def update(self, dt):
        super().update(dt)
        self.tt += dt
        tt = self.tt
        if tt < 6.8:
            self.tito_x = -120 + 57 * tt
            self.walk += dt * 8
        elif tt < 10.0:
            self.walk = 0.0
            if not self.torn and tt >= 7.0:
                self.torn = True
                self.shake = 7.0
                self.app.audio.play("bad")
                self._spill()
        elif tt < 16.0:
            self.dirn = -1
            self.tito_x = 270 - 70 * (tt - 10.0)
            self.walk += dt * 8
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt * 30)
        self._physics(dt)

        nxt = self.line_i + 1
        while nxt < len(INTRO_LINES) and tt >= INTRO_LINES[nxt][0]:
            self.line_i = nxt
            _, self.speaker, self.text = INTRO_LINES[nxt]
            self.chars = 0.0
            self.typing = True
            self.app.audio.play_voice(self.text)
            nxt += 1
        if self.typing:
            self.chars += dt * 42
            if self.chars >= len(self.text):
                self.chars = len(self.text)
                self.typing = False
        if tt >= INTRO_LENGTH:
            self.finish()

    def on_down(self, pos):
        if super().on_down(pos):
            return True
        if self.typing:
            self.chars = len(self.text)
            self.typing = False
        return True

    def on_back(self):
        self.finish()

    def finish(self):
        self.app.audio.stop_voice()
        cb, self.on_done = self.on_done, None
        if cb:
            cb()

    def draw(self, s):
        s.blit(self.sky, (0, 0))
        s.blit(glow(90, (255, 230, 140)), (460 - 90, 110 - 90))
        pygame.draw.circle(s, (255, 236, 150), (460, 110), 42)
        for x, top, w, col in HOUSES:
            pygame.draw.rect(s, col, R(x, top, w, GROUND - top))
            pygame.draw.polygon(s, tuple(max(0, c - 30) for c in col),
                                P([(x - 8, top), (x + w / 2, top - 40), (x + w + 8, top)]))
            for wy in range(top + 20, GROUND - 30, 44):
                for wx in range(x + 14, x + w - 20, 30):
                    pygame.draw.rect(s, (255, 226, 130), R(wx, wy, 14, 18))
        pygame.draw.rect(s, (96, 158, 80), R(0, GROUND, BASE_W, BASE_H - GROUND))
        pygame.draw.rect(s, (70, 130, 60), R(0, GROUND, BASE_W, 6))
        pygame.draw.ellipse(s, (50, 110, 60), R(420, 512, 110, 60))
        if self.tt >= 17.2:
            blink = (self.tt % 3.0) < 0.12
            for ex in (448, 470):
                if not blink:
                    pygame.draw.ellipse(s, (250, 220, 60), R(ex - 7, 508, 14, 10))
                    pygame.draw.line(s, (20, 20, 20), (ex, 508), (ex, 518), 2)
        for it in self.items:
            if it["v"] == "bone":
                draw_bone(s, it["x"], it["y"], 34)
            else:
                draw_gem(s, it["v"], it["x"], it["y"], 12)
        if self.tito_x > -160:
            sx = random.uniform(-self.shake, self.shake) if self.shake > 0 else 0
            speaking = self.speaker == "TITO" and self.typing
            draw_tito(s, self.tito_x + sx, GROUND, 200, self.tt, talk=speaking, walk=self.walk,
                      dirn=self.dirn, bag=True, bag_open=self.torn, sad=self.torn)
        box = R(24, 640, 492, 250)
        pygame.draw.rect(s, (12, 10, 28), box, border_radius=22)
        pygame.draw.rect(s, (120, 100, 200), box, 3, border_radius=22)
        tag = R(40, 604, 270, 48)
        pygame.draw.rect(s, NAME_COLORS[self.speaker], tag, border_radius=14)
        draw_text(s, NAME_TITLES[self.speaker], get_font(26, True), (20, 20, 30),
                  tag.centerx, tag.centery, "center")
        font = get_font(27)
        shown = self.text[:int(self.chars)]
        for i, line in enumerate(wrap_text(shown, font, 440)[:6]):
            draw_text(s, line, font, (245, 245, 255), 50, 668 + i * 36)
        for b in self.buttons:
            b.draw(s)


# ============================================================ ИГРА
class GameScene(Scene):
    def __init__(self, app, n):
        super().__init__(app)
        self.n = n
        self.cfg = make_level(n)
        self.nc = self.cfg["colors"]
        self.bg = gradient(self.cfg["top"], self.cfg["bottom"])
        self.stars_bg = make_stars(50)
        self.ice_surf = make_ice_surf()
        self.infinite = bool(app.save.get("inf_moves"))
        self.moves = self.cfg.get("moves")
        self.time_left = self.cfg.get("time")
        self.score = 0
        self.collected = [0] * len(GEMS)
        self.kills = 0
        self.ice = set()
        self._make_field()
        self.ice_total = len(self.ice)
        self.mon_total = self.monsters_alive()

        self.phase = "idle"
        self.anim_t = 0.0
        self.a = None
        self.b = None
        self.swap_bad = False
        self.pending = set()
        self.pop_cells = set()
        self.pop_t = 0.0
        self.pop_dur = 0.22
        self.blast = None
        self.fall_items = []
        self.fall_dur = 0.3
        self.cascade = 0
        self.selected = None
        self.drag = None
        self.particles = []
        self.texts = []
        self.shake = 0.0
        self.result = None
        self.result_t = 0.0
        self.result_msg = ""
        self.paused = False
        self.card_t = 2.6
        self.ice_surf = make_ice_surf()
        self.pause_btn = Button(R(462, 22, 56, 50), "II", self.pause, (60, 60, 100), 26)
        self.buttons = [self.pause_btn]

    # ---------- создание поля
    def _make_field(self):
        cells = [(r, c) for r in range(ROWS) for c in range(COLS)]
        mons = self.cfg.get("monsters", 0)
        stars = self.app.save.get("start_stars", 0)
        while True:
            self.board = make_board(self.nc)
            random.shuffle(cells)
            k = 0
            for _ in range(mons):
                r, c = cells[k]
                k += 1
                self.board[r][c] = Monster(random.randrange(len(MONSTER_COLORS)))
            for _ in range(stars):
                r, c = cells[k]
                k += 1
                self.board[r][c] = Star()
            if has_possible_move(self.board):
                break
        free = cells[k:]
        self.ice = set(random.sample(free, min(self.cfg.get("ice", 0), len(free))))

    def monsters_alive(self):
        return sum(1 for row in self.board for v in row if isinstance(v, Monster))

    def goals_met(self):
        cfg = self.cfg
        if self.score < cfg.get("score", 0):
            return False
        for k, n in cfg.get("collect", {}).items():
            if self.collected[k] < n:
                return False
        if self.ice:
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
        self.app.go(lambda: GameScene(self.app, self.n))

    def exit_to_menu(self):
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
        if kind == "won":
            save = self.app.save
            save["level"] = max(save["level"], self.n + 1)
            save["best"] = max(save.get("best", 0), self.n)
            write_save(save)
            self.app.audio.play("win")
            self.buttons = [
                Button(R(110, 540, 320, 64), "ДАЛЬШЕ", self.next_level, (255, 150, 60)),
                Button(R(110, 616, 320, 64), "В МЕНЮ", self.exit_to_menu, (150, 90, 220)),
            ]
        else:
            self.app.audio.play("lose")
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

    def try_swap(self, a, b):
        if self.phase != "idle" or self.result or self.paused or self.card_t > 0:
            return
        if self.moves is not None and not self.infinite and self.moves <= 0:
            return
        swap_cells(self.board, a, b)
        matches = find_matches(self.board)
        self.a, self.b = a, b
        self.anim_t = 0.0
        self.cascade = 0
        self.phase = "swap"
        self.swap_bad = not matches
        self.app.audio.play("swap")
        if matches:
            self.pending = matches
            if self.moves is not None and not self.infinite:
                self.moves -= 1
        self.selected = None

    def activate_star(self, cell):
        """Тап по звезде антиматерии: взрыв строки и столбца."""
        r, c = cell
        blast = {(r, i) for i in range(COLS)} | {(i, c) for i in range(ROWS)}
        self.blast = cell
        self.pending = blast
        self.pop_cells = blast
        self.pop_t = 0.0
        self.pop_dur = 0.4
        self.cascade = 0
        self.phase = "pop"
        self.shake = 6.0
        self.app.audio.play("bomb")
        self.selected = None
        self.drag = None

    def _finish_pop(self):
        cells = set(self.pop_cells)
        is_blast = self.blast is not None
        self.blast = None
        gem_cells = [rc for rc in cells if is_gem(self.board[rc[0]][rc[1]])]
        keep = random.choice(gem_cells) if (not is_blast and len(cells) >= 4 and gem_cells) else None

        gain = 0
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
            if (r, c) in self.ice:
                self.ice.discard((r, c))
                self._burst(x, y, (170, 230, 255), 10)

        # монстры: урон, если рядом (или в зоне взрыва) есть совпадение
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
                    self._burst(x, y, MONSTER_COLORS[m.species], 22)

        for (r, c) in cells:
            v = self.board[r][c]
            if isinstance(v, Monster):
                continue
            self.board[r][c] = None
        if keep is not None:
            self.board[keep[0]][keep[1]] = Star()

        self.score += gain
        if cells:
            cx = sum(self._center(r, c)[0] for r, c in cells) / len(cells)
            cy = sum(self._center(r, c)[1] for r, c in cells) / len(cells)
            self._text(f"+{gain}", cx, cy, (255, 230, 120))
            if self.cascade > 1:
                self._text(f"КАСКАД x{self.cascade}!", cx, cy - 40, (255, 150, 90))
        if len(cells) >= 5 or self.cascade >= 2:
            self.shake = max(self.shake, 5.0)
        self.fall_items = gravity_fill(self.board, self.nc)
        maxd = max((dst - src for _, src, dst, _ in self.fall_items), default=1)
        self.fall_dur = 0.18 + 0.045 * maxd
        self.anim_t = 0.0
        self.pop_cells = set()
        self.phase = "fall"
        self.app.audio.play("fall")

    def _end_turn(self):
        self.cascade = 0
        self.phase = "idle"
        if self.goals_met():
            self.set_result("won")
            return
        if not self.infinite and self.moves is not None and self.moves <= 0:
            self.set_result("lost", "Ходы закончились!")
            return
        if not has_possible_move(self.board):
            reshuffle_gems(self.board, self.nc)
            self._text("Перемешали!", BASE_W / 2, BY + 240, (255, 255, 255))

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
                self.pending = matches
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
        if isinstance(self.board[cell[0]][cell[1]], Star):
            self.activate_star(cell)
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
    def _draw_board(self, s):
        ox = oy = 0.0
        if self.shake > 0:
            ox = random.uniform(-self.shake, self.shake)
            oy = random.uniform(-self.shake, self.shake)
        bx, by = BX + ox, BY + oy
        panel = R(bx - 12, by - 12, CELL * COLS + 24, CELL * ROWS + 24)
        pygame.draw.rect(s, (14, 14, 30), panel, border_radius=22)
        pygame.draw.rect(s, (90, 80, 150), panel, 2, border_radius=22)
        for r in range(ROWS):
            for c in range(COLS):
                pygame.draw.rect(s, (36, 36, 64),
                                 R(bx + c * CELL + 4, by + r * CELL + 4, CELL - 8, CELL - 8),
                                 border_radius=12)
        s.set_clip(R(bx, by, CELL * COLS, CELL * ROWS))
        if self.phase == "fall":
            e = ease_out(self.anim_t)
            for v, src, dst, c in self.fall_items:
                y = by + (lerp(src, dst, e) + 0.5) * CELL
                x = bx + c * CELL + CELL / 2
                draw_piece(s, v, x, y, GEM_R, self.t)
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
                    draw_piece(s, v, x, y, rad, self.t)
            if swapping:
                e = ease_in_out(self.anim_t)
                pa = (bx + self.a[1] * CELL + CELL / 2, by + self.a[0] * CELL + CELL / 2)
                pb = (bx + self.b[1] * CELL + CELL / 2, by + self.b[0] * CELL + CELL / 2)
                va = self.board[self.a[0]][self.a[1]]
                vb = self.board[self.b[0]][self.b[1]]
                draw_piece(s, va, lerp(pb[0], pa[0], e), lerp(pb[1], pa[1], e), GEM_R, self.t)
                draw_piece(s, vb, lerp(pa[0], pb[0], e), lerp(pa[1], pb[1], e), GEM_R, self.t)
            if self.blast and self.phase == "pop":
                br, bc = self.blast
                hgt = int(CELL * 0.9 * (1 - self.pop_t))
                if hgt > 2:
                    pygame.draw.rect(s, (235, 220, 255),
                                     R(bx, by + br * CELL + CELL / 2 - hgt / 2, CELL * COLS, hgt))
                    pygame.draw.rect(s, (235, 220, 255),
                                     R(bx + bc * CELL + CELL / 2 - hgt / 2, by, hgt, CELL * ROWS))
        s.set_clip(None)

        for (r, c) in self.ice:
            s.blit(self.ice_surf, (int(bx + c * CELL + 4), int(by + r * CELL + 4)))
        if self.selected and self.phase == "idle":
            r, c = self.selected
            pulse = 2 + int(2 * math.sin(self.t * 8))
            pygame.draw.rect(s, (255, 255, 255),
                             R(bx + c * CELL + 2, by + r * CELL + 2, CELL - 4, CELL - 4),
                             pulse, border_radius=14)

    def _chips(self):
        top = []
        if self.infinite:
            top.append(("ХОДЫ: БЕСК.", (120, 255, 190), None))
        elif self.moves is not None:
            top.append((f"ХОДЫ: {self.moves}", (120, 200, 255), None))
        else:
            mm, ss = int(self.time_left) // 60, int(self.time_left) % 60
            col = (255, 120, 120) if self.time_left < 10 else (255, 200, 120)
            top.append((f"ВРЕМЯ: {mm}:{ss:02d}", col, None))
        st = f"ОЧКИ: {self.score}" + (f" / {self.cfg['score']}" if self.cfg.get("score") else "")
        top.append((st, (255, 210, 90), None))
        goals = []
        for k, n in self.cfg.get("collect", {}).items():
            goals.append((f"{SHAPE_NAMES[k]} {min(self.collected[k], n)}/{n}", GEMS[k][0], k))
        if self.ice_total:
            goals.append((f"ЛЁД {len(self.ice)}/{self.ice_total}", (150, 220, 255), "ice"))
        if self.mon_total:
            goals.append((f"МОНСТРЫ {self.monsters_alive()}/{self.mon_total}", MONSTER_COLORS[0], None))
        return top, goals

    def _draw_hud(self, s):
        draw_portrait(s, 80, 150, 120, self.t)
        label = f"УРОВЕНЬ {self.n}"
        draw_text(s, label, get_font(22, True), (255, 210, 90), 150, 30)
        if self.cfg["hard"]:
            w = get_font(22, True).size(label)[0]
            draw_text(s, "ТЯЖЁЛЫЙ!", get_font(22, True), (255, 90, 90), 150 + w + 14, 30)
        draw_text(s, self.cfg["name"], get_font(34, True), (255, 255, 255), 150, 56)
        top, goals = self._chips()
        x = 30
        for text, col, icon in top:
            x += draw_chip(s, x, 108, text, col, None) + 12
        gx, gy = 30, 156
        for text, col, icon in goals:
            w = chip_width(text, icon)
            if gx + w > 510:
                gx = 30
                gy += 44
            draw_chip(s, gx, gy, text, col, icon)
            gx += w + 10

    def _draw_card(self, s):
        if self.card_t <= 0:
            return
        elapsed = 2.6 - self.card_t
        if elapsed < 0.4:
            off = (1 - ease_out(elapsed / 0.4)) * -260
        elif self.card_t < 0.4:
            off = ease_out((0.4 - self.card_t) / 0.4) * -260
        else:
            off = 0
        panel = R(40, 300 + off, 460, 250)
        pygame.draw.rect(s, (14, 12, 34), panel, border_radius=24)
        pygame.draw.rect(s, (255, 205, 80), panel, 3, border_radius=24)
        cx = 270
        draw_text(s, f"УРОВЕНЬ {self.n}", get_font(26, True), (255, 205, 80), cx, panel.y + 26, "midtop")
        draw_text(s, self.cfg["name"], get_font(38, True), (255, 255, 255), cx, panel.y + 58, "midtop")
        y = panel.y + 110
        for line in wrap_text(goal_text(self.cfg), get_font(23), 410):
            draw_text(s, line, get_font(23), (230, 230, 255), cx, y, "midtop")
            y += 30
        if self.cfg["hard"]:
            draw_text(s, "ТЯЖЁЛЫЙ УРОВЕНЬ! Будь внимателен", get_font(20, True), (255, 110, 110),
                      cx, panel.bottom - 50, "midbottom")
        draw_text(s, self.cfg["hint"], get_font(19), (170, 240, 200), cx, panel.bottom - 22, "midbottom")

    def _draw_result(self, s):
        if not self.result:
            return
        k = ease_out(min(1.0, self.result_t / 0.35))
        w, h = int(440 * k), int(420 * k)
        if w < 4:
            return
        panel = R(270 - w / 2, 470 - h / 2, w, h)
        border = (255, 205, 80) if self.result == "won" else (235, 90, 90)
        pygame.draw.rect(s, (20, 16, 40), panel, border_radius=24)
        pygame.draw.rect(s, border, panel, 3, border_radius=24)
        if self.result_t < 0.25:
            return
        if self.result == "won":
            draw_text(s, f"УРОВЕНЬ {self.n} ПРОЙДЕН!", get_font(30, True), (255, 205, 80), 270, 300, "center")
            body = "Тито гордится тобой! Гав!"
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
        self._draw_hud(s)
        self._draw_board(s)
        draw_text(s, "Подсказка: " + self.cfg["hint"], get_font(20), (225, 225, 245),
                  270, BY + CELL * ROWS + 38, "center")
        draw_text(s, "Свайп или тап — ход. Тап по звезде — взрыв", get_font(18), (180, 180, 210),
                  270, BY + CELL * ROWS + 70, "center")
        for p in self.particles:
            rad = max(1, int(p["size"] * (p["life"] / p["max"])))
            pygame.draw.circle(s, p["color"], (int(p["x"]), int(p["y"])), rad)
        for tx in self.texts:
            draw_text(s, tx["text"], get_font(30, True), tx["color"], tx["x"], tx["y"], "center")
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

