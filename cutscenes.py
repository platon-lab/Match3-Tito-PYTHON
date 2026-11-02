# -*- coding: utf-8 -*-
"""Катсцены: кадры с персонажами, реквизитом, тряской, заголовками и озвучкой."""
import random

import pygame

import art
from config import BG_THEMES
from render import R, gradient, draw_text, wrap_text, get_font, draw_tito, draw_mur, ease_out
from ui import Scene, Button, Bokeh, panel

NAME_COLORS = {"TITO": (255, 205, 80), "MUR": (200, 150, 255), "NAR": (130, 225, 255)}
NAME_TITLES = {"TITO": "Тито", "MUR": "Мурзик", "NAR": "Рассказчик"}


class CutsceneScene(Scene):
    """Проигрывает список реплик (beats). Тап: показать весь текст, потом следующая реплика.
    Вызывает on_done один раз — когда реплики кончились или нажали «Пропустить»."""

    def __init__(self, app, beats, on_done):
        super().__init__(app)
        self.beats = beats
        self.on_done = on_done
        self.idx = -1
        self.cur = beats[0]
        self.bokeh = Bokeh(16)
        self.bg = None
        self.chars = 0.0
        self.typing = False
        self.stage_t = 0.0
        self.shake = 0.0
        self.buttons = [Button(R(372, 24, 144, 46), "Пропустить", self.finish, (60, 60, 90), 22)]
        self._next()

    def _next(self):
        self.idx += 1
        if self.idx >= len(self.beats):
            self.finish()
            return
        b = self.beats[self.idx]
        self.cur = b
        self.bg = gradient(*BG_THEMES.get(b.get("bg", "street"), BG_THEMES["street"]))
        self.chars = 0.0
        self.typing = True
        self.stage_t = 0.0
        self.shake = 7.0 if b.get("shake") else 0.0
        if b.get("sound"):
            self.app.audio.play(b["sound"])
        self.app.audio.play_voice(b["text"])

    def update(self, dt):
        super().update(dt)
        self.stage_t += dt
        self.bokeh.update(dt)
        if self.typing:
            self.chars += dt * 40
            if self.chars >= len(self.cur["text"]):
                self.chars = len(self.cur["text"])
                self.typing = False
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt * 25)

    def on_down(self, pos):
        if super().on_down(pos):
            return True
        if self.typing:
            self.chars = len(self.cur["text"])
            self.typing = False
        else:
            self._next()
        return True

    def on_back(self):
        self.finish()

    def finish(self):
        self.app.audio.stop_voice()
        cb, self.on_done = self.on_done, None
        if cb:
            cb()

    def draw(self, s):
        b = self.cur
        s.blit(self.bg, (0, 0))
        self.bokeh.draw(s)
        ox = random.uniform(-self.shake, self.shake) if self.shake > 0 else 0.0
        oy = random.uniform(-self.shake, self.shake) if self.shake > 0 else 0.0
        cast = b.get("cast", ["TITO"])
        speaker = b["speaker"]

        if b.get("prop"):
            e = ease_out(min(1.0, self.stage_t / 0.5))
            art.draw_prop(s, b["prop"], 300 + ox, 300 - (1 - e) * 60 + oy, 170, self.t)
        floor_y = 560 + oy
        if "TITO" in cast:
            draw_tito(s, 150 + ox, floor_y, 230, self.t, talk=(speaker == "TITO" and self.typing), dirn=1)
        if "MUR" in cast:
            draw_mur(s, 390 + ox, floor_y, 230, self.t, talk=(speaker == "MUR" and self.typing))
        if "BOSS" in cast:
            art.draw_boss(s, b.get("boss", 0), 390 + ox, floor_y, 1.0, self.t,
                          talk=(speaker == "BOSS" and self.typing))

        if b.get("title") and self.stage_t > 0.1:
            e = ease_out(min(1.0, (self.stage_t - 0.1) / 0.4))
            y = 118 - (1 - e) * 40
            draw_text(s, b["title"], get_font(40, True), (255, 220, 120), 270, y, "center")

        box = R(24, 640, 492, 250)
        panel(s, box, fill=(12, 10, 28), border=(120, 100, 200), radius=22, width=3)
        tag_col = b.get("color") or NAME_COLORS.get(speaker, (255, 255, 255))
        name = b.get("name") or NAME_TITLES.get(speaker, "")
        tag = R(40, 604, 270, 48)
        pygame.draw.rect(s, tag_col, tag, border_radius=14)
        draw_text(s, name, get_font(26, True), (20, 20, 30), tag.centerx, tag.centery, "center")

        font = get_font(27)
        shown = b["text"][:int(self.chars)]
        for i, line in enumerate(wrap_text(shown, font, 440)[:6]):
            draw_text(s, line, font, (245, 245, 255), 50, 668 + i * 36)
        hint = "Нажми — показать текст" if self.typing else "Нажми, чтобы продолжить"
        draw_text(s, hint, get_font(20), (190, 190, 230), 270, 912, "center")

        for i in range(len(self.beats)):
            col = (255, 220, 120) if i <= self.idx else (70, 70, 100)
            pygame.draw.circle(s, col, (int(30 + i * 14), 30), 4)
        for btn in self.buttons:
            btn.draw(s)
