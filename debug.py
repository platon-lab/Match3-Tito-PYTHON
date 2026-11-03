# -*- coding: utf-8 -*-
"""Дебаг-меню. Открывается тапом по Тито в главном меню, только если в DEBUG.txt написано ON.
Можно выбрать любой уровень от 1 до 1000 и посмотреть любую катсцену.
Пока играешь из дебаг-меню, прогресс (уровень, рекорд, сохранение, просмотренные механики) не меняется."""
from config import MAX_LEVEL, make_level
from render import R, gradient, draw_text, get_font, make_stars, star_field, wrap_text
from ui import Scene, Button, Bokeh
from scenes import IntroScene
from cutscenes import CutsceneScene
from story import cutscene_catalog

_STATE = {"level": 1, "cut": 0}   # запоминается, пока игра открыта
_CAT = None


def _catalog():
    global _CAT
    if _CAT is None:
        _CAT = cutscene_catalog(MAX_LEVEL)
    return _CAT


def _return(app):
    app.go(lambda: DebugScene(app))


class DebugScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = gradient((40, 12, 46), (6, 4, 14))
        self.stars = make_stars(50)
        self.bokeh = Bokeh(12)
        self.level = _STATE["level"]
        self.cut = _STATE["cut"]
        self.buttons = []
        # уровни: шаг по 1, 10, 100
        for i, d in enumerate((-100, -10, -1, 1, 10, 100)):
            self.buttons.append(Button(R(12 + i * 88, 232, 80, 56), f"{d:+d}",
                                       lambda d=d: self._step_level(d), (110, 80, 180), 22))
        self.buttons.append(Button(R(90, 306, 360, 66), "ИГРАТЬ УРОВЕНЬ", self.play_level,
                                   (255, 150, 60), 26))
        # катсцены: шаг по 1 и 10
        for i, d in enumerate((-10, -1, 1, 10)):
            self.buttons.append(Button(R(40 + i * 115, 484, 100, 52), f"{d:+d}",
                                       lambda d=d: self._step_cut(d), (110, 80, 180), 22))
        self.buttons.append(Button(R(90, 556, 360, 66), "СМОТРЕТЬ КАТСЦЕНУ", self.watch,
                                   (70, 150, 240), 26))
        self.buttons.append(Button(R(90, 638, 360, 56), "ВСТУПЛЕНИЕ", self.watch_intro,
                                   (60, 170, 140), 24))
        self.buttons.append(Button(R(120, 860, 300, 60), "НАЗАД", app.to_menu, (150, 90, 220), 28))

    def _step_level(self, d):
        self.level = min(MAX_LEVEL, max(1, self.level + d))
        _STATE["level"] = self.level

    def _step_cut(self, d):
        self.cut = min(len(_catalog()) - 1, max(0, self.cut + d))
        _STATE["cut"] = self.cut

    def play_level(self):
        self.app.debug_play = True
        self.app.play_level(self.level)

    def watch(self):
        app = self.app
        _, beats = _catalog()[self.cut]
        app.go(lambda: CutsceneScene(app, beats, lambda: _return(app)))

    def watch_intro(self):
        app = self.app
        app.go(lambda: IntroScene(app, lambda: _return(app)))

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        star_field(s, self.stars, self.t)
        self.bokeh.draw(s)
        draw_text(s, "ДЕБАГ-МЕНЮ", get_font(46, True), (255, 120, 220), 270, 60, "center")

        cfg = make_level(self.level)
        draw_text(s, f"УРОВЕНЬ {self.level}", get_font(40, True), (255, 255, 255), 270, 118, "center")
        tag = cfg["name"]
        if cfg["boss"]:
            tag += " · БОСС"
        elif cfg["hard"]:
            tag += " · тяжёлый"
        draw_text(s, tag, get_font(22), (190, 220, 255), 270, 170, "center")

        cat = _catalog()
        label, _ = cat[self.cut]
        draw_text(s, f"КАТСЦЕНА {self.cut + 1} из {len(cat)}", get_font(20, True), (255, 210, 120),
                  270, 404, "center")
        for i, line in enumerate(wrap_text(label, get_font(22), 440)[:2]):
            draw_text(s, line, get_font(22), (240, 240, 255), 270, 428 + i * 26, "center")

        super().draw(s)
