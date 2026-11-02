# -*- coding: utf-8 -*-
"""Босс-бой каждые 50 уровней. У каждого из 6 боссов свой набор атак.
Когда у босса остаётся половина здоровья, он звереет: атакует чаще и сильнее."""
import math
import random

import pygame

import art
from config import BASE_W, BASE_H, BOSS_NAMES, BOSS_COLORS, BOSS_EVERY, write_save
from render import (gradient, star_field, make_stars, draw_text, get_font, draw_tito, draw_bone,
                    draw_heart, R)
from ui import Scene, Button, Bokeh
from story import RESULT_LOST, RESULT_BOSS_WON

TITO_Y = 900      # подошва Тито
BOSS_Y = 340      # подошва босса

# атаки каждого босса (по порядку BOSS_NAMES)
PATTERNS = [
    ["spread", "aim", "rain"],        # Мурзик-гигант
    ["rain", "wave", "sweep"],        # Слизень-король
    ["seek", "spread"],               # Летучая мышь-барон
    ["aim", "wave", "ring"],          # Призрак-граф
    ["ring", "spread", "sweep"],      # Паук-королева
    ["aim", "seek", "sweep"],         # Циклоп-колосс
]


class BossScene(Scene):
    def __init__(self, app, n):
        super().__init__(app)
        self.n = n
        self.b = max(1, n // BOSS_EVERY)           # номер босса
        self.kind = (self.b - 1) % len(BOSS_NAMES)  # какой босс
        self.name = BOSS_NAMES[self.kind]
        self.color = BOSS_COLORS[self.kind]
        self.pats = PATTERNS[self.kind]
        self.bg = gradient((70, 20, 60), (12, 8, 26))
        self.stars = make_stars(60)
        self.bokeh = Bokeh(16)
        self.hp_max = 30 + 10 * self.b          # здоровье растёт с номером босса
        tier = min(self.b, 6)                   # атаки растут только до шестого босса
        self.hp = self.hp_max
        self.bx = 270.0
        self.bdir = 1
        self.bspeed = min(260.0, 60.0 + 22.0 * tier)
        self.tx = 270.0
        self.tgt = 270.0
        self.moving = False
        self.touching = False
        self.lives = 5
        self.invuln = 0.0
        self.my = []        # выстрелы Тито: [x, y]
        self.enemy = []     # выстрелы босса: [x, y, vx, vy] или [x, y, vx, vy, "seek"]
        self.shot_cd = 0.0
        self.atk_cd = 1.5
        self.atk_gap = max(1.0, 2.3 - 0.1 * tier)
        self.shots_per = min(6, 1 + tier)
        self.bul_speed = 200.0 + 20.0 * tier
        self.enraged = False
        self.msg = ""
        self.msg_t = 0.0
        self.result = None
        self.result_t = 0.0
        self.buttons = []

    # ---------- управление: тянем пальцем влево-вправо, Тито следует
    def on_down(self, pos):
        if super().on_down(pos):
            return True
        if self.result is None:
            self.touching = True
            self.tgt = min(500, max(40, pos[0]))
        return True

    def on_motion(self, pos):
        super().on_motion(pos)
        if self.touching and self.result is None:
            self.tgt = min(500, max(40, pos[0]))

    def on_up(self, pos):
        self.touching = False
        return super().on_up(pos)

    def on_back(self):
        self.app.to_menu()

    # ---------- атаки
    def _attack(self):
        pat = random.choice(self.pats)
        sp = self.bul_speed
        k = self.shots_per
        bx, by0 = self.bx, BOSS_Y - 40
        if pat == "spread":
            for i in range(k):
                a = -0.7 + 1.4 * i / max(1, k - 1)
                self.enemy.append([bx, by0, math.sin(a) * sp, math.cos(a) * sp])
        elif pat == "aim":
            for _ in range(1 + min(2, self.b // 2)):
                dx = self.tx - bx
                dy = (TITO_Y - 60) - by0
                d = math.hypot(dx, dy) or 1.0
                self.enemy.append([bx, by0, dx / d * sp * 1.15, dy / d * sp * 1.15])
        elif pat == "rain":
            for _ in range(k):
                self.enemy.append([random.uniform(30, BASE_W - 30), -20,
                                   random.uniform(-40, 40), sp * 0.8])
        elif pat == "wave":
            base = random.uniform(-0.4, 0.4)
            for i in range(k):
                a = base + (i - k / 2) * 0.12
                self.enemy.append([bx, by0, math.sin(a) * sp, math.cos(a) * sp])
        elif pat == "seek":
            for _ in range(1 + min(1, self.b // 3)):
                self.enemy.append([bx, by0, 0.0, sp * 0.75, "seek"])
        elif pat == "ring":
            m = max(8, k)
            for i in range(m):
                a = math.tau * i / m
                self.enemy.append([bx, by0, math.cos(a) * sp * 0.8, math.sin(a) * sp * 0.8])
        elif pat == "sweep":
            # стена с проходом: надо увернуться в просвет
            gap = random.randrange(0, 10)
            for i in range(13):
                if i in (gap, gap + 1, gap + 2):
                    continue
                self.enemy.append([20 + i * 42, -20, 0.0, sp * 0.6])

    def _finish(self, won):
        self.result = "won" if won else "lost"
        self.result_t = 0.0
        self.touching = False
        if won:
            self.app.audio.play("win")
            self.app.audio.play_voice(RESULT_BOSS_WON)
            save = self.app.save
            save["level"] = max(save["level"], self.n + 1)
            save["best"] = max(save.get("best", 0), self.n)
            write_save(save)
            self.buttons = [
                Button(R(110, 600, 320, 64), "ДАЛЬШЕ", lambda: self.app.play_level(self.n + 1), (255, 150, 60)),
                Button(R(110, 680, 320, 64), "В МЕНЮ", self.app.to_menu, (150, 90, 220)),
            ]
        else:
            self.app.audio.play("lose")
            self.app.audio.play_voice(RESULT_LOST)
            self.buttons = [
                Button(R(110, 600, 320, 64), "ЗАНОВО", lambda: self.app.go(lambda: BossScene(self.app, self.n)),
                       (70, 150, 240)),
                Button(R(110, 680, 320, 64), "В МЕНЮ", self.app.to_menu, (150, 90, 220)),
            ]

    # ---------- логика
    def update(self, dt):
        super().update(dt)
        self.bokeh.update(dt)
        if self.msg_t > 0:
            self.msg_t = max(0.0, self.msg_t - dt)
        if self.result:
            self.result_t += dt
            return

        if not self.enraged and self.hp <= self.hp_max // 2:
            self.enraged = True
            self.atk_gap *= 0.7
            self.shots_per += 2
            self.msg, self.msg_t = "БОСС ЗВЕРЕЕТ!", 2.0
            self.app.audio.play("roar")

        self.moving = abs(self.tgt - self.tx) > 4
        self.tx += (self.tgt - self.tx) * min(1.0, dt * 10)
        self.bx += self.bdir * self.bspeed * dt
        if self.bx < 120:
            self.bx, self.bdir = 120, 1
        if self.bx > 420:
            self.bx, self.bdir = 420, -1

        # стрельба Тито
        self.shot_cd -= dt
        if self.shot_cd <= 0:
            self.shot_cd = 0.3
            self.my.append([self.tx, TITO_Y - 100])
            self.app.audio.play("shot")

        # атаки босса
        self.atk_cd -= dt
        if self.atk_cd <= 0:
            self.atk_cd = self.atk_gap
            self._attack()

        self.invuln = max(0.0, self.invuln - dt)

        # косточки летят вверх и попадают по боссу
        keep = []
        for b in self.my:
            b[1] -= 640 * dt
            hit = abs(b[0] - self.bx) < 115 and (BOSS_Y - 240) < b[1] < BOSS_Y
            if hit:
                self.hp -= 1
                self.app.audio.play("boom")
            elif b[1] > -20:
                keep.append(b)
        self.my = keep

        # снаряды босса
        keep = []
        hit_tito = False
        for e in self.enemy:
            if len(e) > 4 and e[4] == "seek":
                e[2] = max(-190.0, min(190.0, e[2] + (self.tx - e[0]) * dt * 0.9))
            e[0] += e[2] * dt
            e[1] += e[3] * dt
            if not (-40 < e[0] < BASE_W + 40 and -60 < e[1] < BASE_H + 40):
                continue
            if self.invuln <= 0 and abs(e[0] - self.tx) < 36 and abs(e[1] - (TITO_Y - 60)) < 55:
                hit_tito = True
                continue
            keep.append(e)
        self.enemy = keep
        if hit_tito:
            self.lives -= 1
            self.invuln = 1.6
            self.app.audio.play("hit")
            if self.lives <= 0:
                self._finish(False)
                return
        if self.hp <= 0:
            self.hp = 0
            self._finish(True)

    # ---------- отрисовка
    def draw(self, s):
        s.blit(self.bg, (0, 0))
        star_field(s, self.stars, self.t)
        self.bokeh.draw(s)

        art.draw_boss(s, self.kind, self.bx, BOSS_Y, 1.0, self.t, talk=int(self.t * 3) % 2 == 0)

        # полоска здоровья босса
        pygame.draw.rect(s, (40, 20, 30), R(40, 24, 460, 22), border_radius=10)
        frac = max(0.0, self.hp / self.hp_max)
        bar_col = (255, 120, 60) if self.enraged else (235, 70, 90)
        pygame.draw.rect(s, bar_col, R(40, 24, 460 * frac, 22), border_radius=10)
        draw_text(s, f"БОСС {self.b}: {self.name.upper()}", get_font(20, True), (255, 255, 255),
                  270, 60, "center")

        # Тито (мигает, когда неуязвим)
        blink_off = self.invuln > 0 and int(self.invuln * 12) % 2 == 0
        if not blink_off:
            walk = self.t * 8 if self.moving else 0.0
            draw_tito(s, self.tx, TITO_Y, 170, self.t, walk=walk)

        for x, y in self.my:
            draw_bone(s, x, y, 24)
        shot_col = (255, 110, 110) if self.enraged else (150, 150, 165)
        for e in self.enemy:
            pygame.draw.circle(s, shot_col, (int(e[0]), int(e[1])), 12)
            pygame.draw.circle(s, (90, 90, 105), (int(e[0]), int(e[1])), 12, 2)

        for i in range(self.lives):
            draw_heart(s, 50 + i * 42, 880, 9)

        draw_text(s, "Тяни пальцем влево-вправо, Тито стреляет сам", get_font(18),
                  (220, 200, 230), 270, 935, "center")
        if self.msg_t > 0:
            draw_text(s, self.msg, get_font(34, True), (255, 120, 60), 270, 430, "center")

        if self.result:
            self._draw_result(s)
        for b in self.buttons:
            b.draw(s)

    def _draw_result(self, s):
        k = min(1.0, self.result_t / 0.35)
        pw, ph = int(440 * k), int(300 * k)
        if pw < 4:
            return
        panel_rect = R(270 - pw / 2, 470 - ph / 2, pw, ph)
        col = (255, 205, 80) if self.result == "won" else (235, 90, 90)
        pygame.draw.rect(s, (20, 16, 40), panel_rect, border_radius=24)
        pygame.draw.rect(s, col, panel_rect, 3, border_radius=24)
        if self.result_t < 0.25:
            return
        if self.result == "won":
            draw_text(s, "БОСС ПОВЕРЖЕН!", get_font(34, True), (255, 205, 80), 270, 360, "center")
            draw_text(s, f"{self.name} отступает, косточка почти у Тито!", get_font(20),
                      (230, 230, 255), 270, 410, "center")
        else:
            draw_text(s, "ТИТО ПОВЕРЖЕН", get_font(34, True), (240, 110, 110), 270, 360, "center")
            draw_text(s, "Попробуем ещё раз! Гав!", get_font(22), (230, 230, 255), 270, 410, "center")
