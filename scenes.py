# -*- coding: utf-8 -*-
"""Вступление: анимированная история Тито (ничего не идёт, пока не нажмёшь)."""
import random

import pygame

from config import BASE_W, BASE_H, GEMS, INTRO_LINES, INTRO_LENGTH
from render import (get_font, draw_text, wrap_text, R, P, gradient, glow, draw_gem, draw_tito,
                    draw_bone)
from ui import Scene, Button

NAME_COLORS = {"TITO": (255, 205, 80), "MUR": (200, 150, 255), "NAR": (130, 225, 255)}
NAME_TITLES = {"TITO": "Тито", "MUR": "Мурзик", "NAR": "Рассказчик"}
GROUND = 560
HOUSES = [(10, 330, 120, (170, 120, 100)), (140, 300, 110, (150, 110, 120)),
          (260, 350, 130, (120, 140, 170)), (400, 320, 130, (180, 140, 110))]


class IntroScene(Scene):
    """Ничего не идёт, пока не нажмёшь. Каждая реплика ждёт тапа.
    Тап во время движения — перемотка, тап во время текста — показать весь текст."""

    def __init__(self, app, on_done):
        super().__init__(app)
        self.on_done = on_done
        self.sky = gradient((90, 160, 235), (210, 235, 255))
        self.rng = random.Random(7)
        self.phase = "start"      # start -> run -> talk -> run -> ... -> end
        self.tt = 0.0             # время сцены
        self.goal = 0.0           # до какого времени сцена идёт
        self.rate = 1.0
        self.next_idx = 0         # номер следующей реплики
        self.tito_x = -120.0
        self.dirn = 1
        self.walk = 0.0
        self.torn = False
        self.items = []
        self.shake = 0.0
        self.chars = 0.0
        self.typing = False
        self.speaker = "NAR"
        self.text = ""
        self.buttons = [Button(R(372, 24, 144, 46), "Пропустить", self.finish, (60, 60, 90), 22)]

    # ---------- тайминг
    def _arrive(self):
        if self.next_idx < len(INTRO_LINES):
            _, speaker, text = INTRO_LINES[self.next_idx]
            self.speaker, self.text = speaker, text
            self.chars = 0.0
            self.typing = True
            self.phase = "talk"
            self.next_idx += 1
            self.app.audio.play_voice(text)
        else:
            self.phase = "end"

    def _advance(self):
        if self.next_idx < len(INTRO_LINES):
            self.goal = INTRO_LINES[self.next_idx][0]
        else:
            self.goal = INTRO_LENGTH
        self.phase = "run"
        self.app.audio.stop_voice()

    def _spill(self):
        """Рюкзак рвётся: самоцветы и косточка падают на дорогу."""
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

    def _animate(self, dt):
        tt = self.tt
        moving = self.phase == "run" and (tt < 6.8 or 10.0 <= tt < 16.0)
        if tt < 6.8:
            self.tito_x = -120 + 57 * tt
        elif tt < 10.0:
            self.tito_x = 267.6
        else:
            self.tito_x = 267.6 - 70 * (tt - 10.0)
        self.dirn = 1 if tt < 10.0 else -1
        self.walk = self.walk + dt * 8 if moving else 0.0
        if not self.torn and tt >= 7.0:
            self.torn = True
            self.shake = 7.0
            self.app.audio.play("bad")
            self._spill()
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt * 30)
        self._physics(dt)

    # ---------- цикл
    def update(self, dt):
        super().update(dt)
        if self.phase == "run":
            self.tt = min(self.goal, self.tt + dt * self.rate)
            if self.tt >= self.goal:
                self.rate = 1.0
                self._arrive()
        if self.phase == "talk" and self.typing:
            self.chars += dt * 42
            if self.chars >= len(self.text):
                self.chars = len(self.text)
                self.typing = False
        self._animate(dt)

    def on_down(self, pos):
        if super().on_down(pos):
            return True
        if self.phase == "start":
            self.phase = "run"
            self.goal = INTRO_LINES[0][0]
        elif self.phase == "run":
            self.rate = 4.0
        elif self.phase == "talk":
            if self.typing:
                self.chars = len(self.text)
                self.typing = False
            else:
                self._advance()
        elif self.phase == "end":
            self.finish()
        return True

    def on_back(self):
        self.finish()

    def finish(self):
        self.app.audio.stop_voice()
        cb, self.on_done = self.on_done, None
        if cb:
            cb()

    # ---------- отрисовка
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
            sx = random.uniform(-self.shake, self.shake) if self.shake > 0 else 0.0
            draw_tito(s, self.tito_x + sx, GROUND, 200, self.tt,
                      talk=self.typing and self.speaker == "TITO", walk=self.walk,
                      dirn=self.dirn, bag=True, bag_open=self.torn, sad=self.torn)

        box = R(24, 640, 492, 250)
        pygame.draw.rect(s, (12, 10, 28), box, border_radius=22)
        pygame.draw.rect(s, (120, 100, 200), box, 3, border_radius=22)
        if self.phase == "start":
            speaker, text = "NAR", "Тито ждёт. Нажми на экран, чтобы начать историю."
            hint = "Нажми, чтобы начать"
        else:
            speaker, text = self.speaker, self.text
            if self.phase == "run":
                hint = "Нажми — перемотать"
            elif self.phase == "talk":
                hint = "Нажми — показать текст" if self.typing else "Нажми, чтобы продолжить"
            else:
                hint = "Нажми, чтобы начать игру"
        tag = R(40, 604, 270, 48)
        pygame.draw.rect(s, NAME_COLORS[speaker], tag, border_radius=14)
        draw_text(s, NAME_TITLES[speaker], get_font(26, True), (20, 20, 30),
                  tag.centerx, tag.centery, "center")
        font = get_font(27)
        shown = text if self.phase == "start" else text[:int(self.chars)]
        for i, line in enumerate(wrap_text(shown, font, 440)[:6]):
            draw_text(s, line, font, (245, 245, 255), 50, 668 + i * 36)
        draw_text(s, hint, get_font(20), (190, 190, 230), 270, 912, "center")
        for b in self.buttons:
            b.draw(s)
