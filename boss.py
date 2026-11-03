# -*- coding: utf-8 -*-
"""Босс-бой каждые 50 уровней (всего 20 боссов). Новый баланс:
- перед каждой атакой босс предупреждает: вспыхивает жёлтый круг и подсказка, куда уходить;
- атаки реже, снарядов меньше, в «стене» проход шире;
- жизней 6, и одна восстанавливается, если Тито давно не получал удар;
- здоровье босса растёт медленнее;
- в ярости (на трети здоровья) босс атакует чаще, но предупреждает так же."""
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
MAX_LIVES = 6
WARN_TIME = 0.9   # сколько секунд предупреждения перед атакой
HEAL_EVERY = 14.0 # секунд без ударов до восстановления жизни

# атаки каждого из 6 рисунков боссов
PATTERNS = [
    ["spread", "aim", "rain"],        # Мурзик
    ["rain", "wave", "sweep"],        # Слизень
    ["seek", "spread"],               # Летучая мышь
    ["aim", "wave", "ring"],          # Призрак
    ["ring", "spread", "sweep"],      # Паук
    ["aim", "seek", "sweep"],         # Циклоп
]

PAT_HINTS = {
    "spread": "Веер косточек: ищи просвет между ними",
    "aim": "Прицельный выстрел: отойди в сторону",
    "rain": "Дождь сверху: не стой под ним",
    "wave": "Волна: уходи от её центра",
    "seek": "Самонаводка: медленно уводит за тобой, беги",
    "ring": "Кольцо снарядов: найди промежуток",
    "sweep": "Стена с проходом: лети в просвет",
}


class BossScene(Scene):
    def __init__(self, app, n):
        super().__init__(app)
        self.n = n
        self.b = max(1, n // BOSS_EVERY)              # номер босса
        self.idx = (self.b - 1) % len(BOSS_NAMES)     # какой из 20 боссов
        self.kind = self.idx % 6                      # какой рисунок
        self.name = BOSS_NAMES[self.idx]
        self.color = BOSS_COLORS[self.idx]
        self.pats = PATTERNS[self.kind]
        self.bg = gradient((70, 20, 60), (12, 8, 26))
        self.stars = make_stars(60)
        self.bokeh = Bokeh(16)
        self.hp_max = 16 + 3 * self.b                 # здоровье растёт медленнее, чем раньше
        tier = min(self.b, 8)
        self.hp = self.hp_max
        self.bx = 270.0
        self.bdir = 1
        self.bspeed = min(170.0, 50.0 + 12.0 * tier)
        self.tx = 270.0
        self.tgt = 270.0
        self.moving = False
        self.touching = False
        self.lives = MAX_LIVES
        self.invuln = 0.0
        self.heal_t = 0.0
        self.my = []          # выстрелы Тито: [x, y]
        self.enemy = []       # выстрелы босса: [x, y, vx, vy] или [x, y, vx, vy, "seek"]
        self.shot_cd = 0.0
        self.atk_cd = 2.0
        self.atk_gap = max(1.8, 3.2 - 0.12 * tier)
        self.shots_per = min(5, 3 + tier // 3)
        self.bul_speed = 150.0 + 12.0 * tier
        self.pending = None   # атака, которая сейчас предупреждает
        self.warn_t = 0.0
        self.enraged = False
        self.msg = ""
        self.msg_t = 0.0
        self.result = None
        self.result_t = 0.0
        self.buttons = []

    def _say(self, text, t):
        self.msg, self.msg_t = text, t

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
    def _attack(self, pat):
        sp = self.bul_speed
        k = self.shots_per
        bx, by0 = self.bx, BOSS_Y - 40
        if pat == "spread":
            for i in range(k):
                a = -0.7 + 1.4 * i / max(1, k - 1)
                self.enemy.append([bx, by0, math.sin(a) * sp, math.cos(a) * sp])
        elif pat == "aim":
            for _ in range(1 + min(1, self.b // 4)):
                dx = self.tx - bx
                dy = (TITO_Y - 60) - by0
                d = math.hypot(dx, dy) or 1.0
                self.enemy.append([bx, by0, dx / d * sp * 1.05, dy / d * sp * 1.05])
        elif pat == "rain":
            for _ in range(k):
                self.enemy.append([random.uniform(30, BASE_W - 30), -20,
                                   random.uniform(-30, 30), sp * 0.7])
        elif pat == "wave":
            base = random.uniform(-0.4, 0.4)
            for i in range(k):
                a = base + (i - k / 2) * 0.14
                self.enemy.append([bx, by0, math.sin(a) * sp, math.cos(a) * sp])
        elif pat == "seek":
            self.enemy.append([bx, by0, 0.0, sp * 0.6, "seek"])
        elif pat == "ring":
            m = max(8, k + 3)
            for i in range(m):
                a = math.tau * i / m
                self.enemy.append([bx, by0, math.cos(a) * sp * 0.7, math.sin(a) * sp * 0.7])
        elif pat == "sweep":
            # стена с широким проходом (4 клетки)
            gap = random.randrange(0, 9)
            for i in range(13):
                if gap <= i <= gap + 3:
                    continue
                self.enemy.append([20 + i * 42, -20, 0.0, sp * 0.5])

    def _finish(self, won):
        self.result = "won" if won else "lost"
        self.result_t = 0.0
        self.touching = False
        self.pending = None
        dbg = self.app.debug_play
        if won:
            self.app.audio.play("win")
            self.app.audio.play_voice(RESULT_BOSS_WON)
            if not dbg:
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

        if not self.enraged and self.hp <= self.hp_max // 3:
            self.enraged = True
            self.atk_gap *= 0.75
            self.shots_per = min(6, self.shots_per + 1)
            self._say("БОСС ЗВЕРЕЕТ!", 2.0)
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

        # атаки босса: сначала предупреждение, потом выстрел
        self.atk_cd -= dt
        if self.pending is None and self.atk_cd <= 0:
            self.pending = random.choice(self.pats)
            self.warn_t = WARN_TIME
            self.app.audio.play("tick")
        if self.pending is not None:
            self.warn_t -= dt
            if self.warn_t <= 0:
                self._attack(self.pending)
                self.pending = None
                self.atk_cd = self.atk_gap

        self.invuln = max(0.0, self.invuln - dt)

        # жизнь восстанавливается, если давно не получали удар
        if self.lives < MAX_LIVES:
            self.heal_t += dt
            if self.heal_t >= HEAL_EVERY:
                self.heal_t = 0.0
                self.lives += 1
                self._say("Тито восстановил силы!", 1.5)
        else:
            self.heal_t = 0.0

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
                e[2] = max(-170.0, min(170.0, e[2] + (self.tx - e[0]) * dt * 0.7))
            e[0] += e[2] * dt
            e[1] += e[3] * dt
            if not (-40 < e[0] < BASE_W + 40 and -60 < e[1] < BASE_H + 40):
                continue
            if self.invuln <= 0 and abs(e[0] - self.tx) < 34 and abs(e[1] - (TITO_Y - 60)) < 50:
                hit_tito = True
                continue
            keep.append(e)
        self.enemy = keep
        if hit_tito:
            self.lives -= 1
            self.invuln = 1.2
            self.heal_t = 0.0
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

        if self.pending is not None:
            pulse = 0.5 + 0.5 * math.sin(self.t * 18)
            pygame.draw.circle(s, (255, 220, 90), (int(self.bx), int(BOSS_Y)), int(125 + 8 * pulse), 4)
            draw_text(s, "!", get_font(48, True), (255, 220, 90), self.bx, BOSS_Y - 150, "center")
            draw_text(s, PAT_HINTS[self.pending], get_font(20, True), (255, 230, 170), 270, 470, "center")

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
            draw_heart(s, 50 + i * 40, 880, 9)

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
