# -*- coding: utf-8 -*-
"""Босс-бой: каждые 100 уровней. Тито стреляет косточками, Мурзик-гигант кидает шерсть."""
import math
import random

import pygame

from config import BASE_W, BASE_H, write_save
from render import (gradient, star_field, make_stars, draw_text, get_font, draw_tito,
                    draw_mur, draw_bone, draw_heart, R, glow)
from scenes import Scene, Button

TITO_Y = 900      # подошва Тито
BOSS_Y = 340      # подошва Мурзика-босса


class BossScene(Scene):
    def __init__(self, app, n):
        super().__init__(app)
        self.n = n
        self.bno = max(1, n // 100)
        self.bg = gradient((70, 20, 60), (12, 8, 26))
        self.stars = make_stars(80)
        self.hp_max = 40 + 30 * self.bno
        self.hp = self.hp_max
        self.bx = 270.0
        self.bdir = 1
        self.bspeed = min(300.0, 70.0 + 28.0 * self.bno)
        self.tx = 270.0
        self.tgt = 270.0
        self.moving = False
        self.touching = False
        self.lives = 3
        self.invuln = 0.0
        self.my = []        # выстрелы Тито: [x, y]
        self.enemy = []     # шерсть Мурзика: [x, y, vx, vy]
        self.shot_cd = 0.0
        self.atk_cd = 1.5
        self.atk_gap = max(0.55, 1.6 - 0.12 * self.bno)
        self.shots_per = min(9, 3 + self.bno)
        self.bul_speed = 210.0 + 40.0 * self.bno
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

    # ---------- логика
    def _attack(self):
        sp = self.bul_speed
        pat = random.choice(["spread", "aim", "rain"])
        if pat == "spread":
            for i in range(self.shots_per):
                a = -0.9 + 1.8 * i / max(1, self.shots_per - 1)
                self.enemy.append([self.bx, BOSS_Y - 40, math.sin(a) * sp, math.cos(a) * sp])
        elif pat == "aim":
            for _ in range(1 + self.bno // 2):
                dx = self.tx - self.bx
                dy = (TITO_Y - 60) - (BOSS_Y - 40)
                d = math.hypot(dx, dy) or 1.0
                self.enemy.append([self.bx, BOSS_Y - 40, dx / d * sp * 1.15, dy / d * sp * 1.15])
        else:
            for _ in range(self.shots_per):
                self.enemy.append([random.uniform(30, BASE_W - 30), -20,
                                   random.uniform(-40, 40), sp * 0.8])

    def _finish(self, won):
        self.result = "won" if won else "lost"
        self.result_t = 0.0
        self.touching = False
        if won:
            self.app.audio.play("win")
            save = self.app.save
            save["level"] = max(save["level"], self.n + 1)
            save["best"] = max(save.get("best", 0), self.n)
            write_save(save)
            self.buttons = [
                Button(R(110, 600, 320, 64), "ДАЛЬШЕ", lambda: self.app.play_level(self.n + 1),
                       (255, 150, 60)),
                Button(R(110, 680, 320, 64), "В МЕНЮ", self.app.to_menu, (150, 90, 220)),
            ]
        else:
            self.app.audio.play("lose")
            self.buttons = [
                Button(R(110, 600, 320, 64), "ЗАНОВО", lambda: self.app.go(lambda: BossScene(self.app, self.n)),
                       (70, 150, 240)),
                Button(R(110, 680, 320, 64), "В МЕНЮ", self.app.to_menu, (150, 90, 220)),
            ]

    def update(self, dt):
        super().update(dt)
        if self.result:
            self.result_t += dt
            return

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

        # атаки Мурзика
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

        # шерсть Мурзика
        keep = []
        hit_tito = False
        for e in self.enemy:
            e[0] += e[2] * dt
            e[1] += e[3] * dt
            if not (-30 < e[0] < BASE_W + 30 and e[1] < BASE_H + 30):
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
        s.blit(glow(120, (255, 240, 200)), (int(BASE_W - 150), 40))
        pygame.draw.circle(s, (255, 240, 200), (BASE_W - 90, 100), 36)

        draw_mur(s, self.bx, BOSS_Y, 280, self.t, talk=int(self.t * 3) % 2 == 0)

        # полоска здоровья босса
        pygame.draw.rect(s, (40, 20, 30), R(40, 24, 460, 22), border_radius=10)
        frac = max(0.0, self.hp / self.hp_max)
        pygame.draw.rect(s, (235, 70, 90), R(40, 24, 460 * frac, 22), border_radius=10)
        draw_text(s, f"БОСС №{self.bno}: МУРЗИК-ГИГАНТ", get_font(22, True), (255, 255, 255),
                  270, 60, "center")

        # Тито (мигает, когда неуязвим)
        blink_off = self.invuln > 0 and int(self.invuln * 12) % 2 == 0
        if not blink_off:
            walk = self.t * 8 if self.moving else 0.0
            draw_tito(s, self.tx, TITO_Y, 170, self.t, walk=walk)

        for x, y in self.my:
            draw_bone(s, x, y, 24)
        for e in self.enemy:
            pygame.draw.circle(s, (150, 150, 165), (int(e[0]), int(e[1])), 12)
            pygame.draw.circle(s, (90, 90, 105), (int(e[0]), int(e[1])), 12, 2)

        for i in range(self.lives):
            draw_heart(s, 50 + i * 42, 880, 9)

        draw_text(s, "Тяни пальцем влево-вправо, Тито стреляет сам", get_font(18),
                  (220, 200, 230), 270, 935, "center")

        if self.result:
            self._draw_result(s)
        for b in self.buttons:
            b.draw(s)

    def _draw_result(self, s):
        k = min(1.0, self.result_t / 0.35)
        pw, ph = int(440 * k), int(300 * k)
        if pw < 4:
            return
        panel = R(270 - pw / 2, 470 - ph / 2, pw, ph)
        col = (255, 205, 80) if self.result == "won" else (235, 90, 90)
        pygame.draw.rect(s, (20, 16, 40), panel, border_radius=24)
        pygame.draw.rect(s, col, panel, 3, border_radius=24)
        if self.result_t < 0.25:
            return
        if self.result == "won":
            draw_text(s, "БОСС ПОВЕРЖЕН!", get_font(34, True), (255, 205, 80), 270, 360, "center")
            draw_text(s, "Мурзик отступает, косточка почти у Тито!", get_font(22), (230, 230, 255),
                      270, 410, "center")
        else:
            draw_text(s, "ТИТО ПОВЕРЖЕН", get_font(34, True), (240, 110, 110), 270, 360, "center")
            draw_text(s, "Попробуем ещё раз! Гав!", get_font(22), (230, 230, 255), 270, 410, "center")
