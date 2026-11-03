# -*- coding: utf-8 -*-
"""Меню: главный экран, выбор уровня, настройки."""
import math

from config import BOSS_EVERY, write_save, debug_enabled
from render import R, gradient, make_stars, star_field, draw_text, get_font, draw_portrait
from ui import Scene, Button, Bokeh, chips_centered
from game import GameScene
from debug import DebugScene

TITO_TAP = R(160, 400, 220, 220)   # область тапа по Тито (работает только при ON в DEBUG.txt)
PER_PAGE = 20


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = gradient((46, 24, 86), (8, 8, 22))
        self.stars = make_stars(60)
        self.bokeh = Bokeh(18)
        self.debug = debug_enabled()
        game = app.save.get("game")
        if game and game.get("n"):
            primary = Button(R(90, 540, 360, 70), "ПРОДОЛЖИТЬ", self.continue_game, (255, 150, 60))
        else:
            primary = Button(R(90, 540, 360, 70), "ИГРАТЬ", self.play, (255, 150, 60))
        self.buttons = [
            primary,
            Button(R(90, 626, 360, 70), "ВЫБОР УРОВНЯ", self.levels, (70, 150, 240)),
            Button(R(90, 712, 360, 70), "НАСТРОЙКИ", self.settings, (60, 170, 140)),
            Button(R(90, 798, 360, 70), "ВЫХОД", self.quit_game, (200, 70, 80)),
        ]

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        star_field(s, self.stars, self.t)
        self.bokeh.draw(s)
        bob = math.sin(self.t * 2) * 4
        draw_text(s, "ТИТО", get_font(124, True), (70, 30, 0), 274, 128 + bob, "center")
        draw_text(s, "ТИТО", get_font(124, True), (255, 200, 60), 270, 124 + bob, "center")
        draw_text(s, "ТРИ В РЯД", get_font(40, True), (110, 230, 255), 270, 196, "center")
        save = self.app.save
        chips_centered(s, 236, [(f"Уровень {save['level']}", (255, 210, 90)),
                                (f"Рекорд {save.get('best', 0)}", (150, 220, 255))])
        draw_portrait(s, 270, 510 + math.sin(self.t * 3) * 4, 220, self.t,
                      blink=(self.t % 4) < 0.12)
        if self.debug:
            draw_text(s, "DEBUG", get_font(16, True), (255, 120, 220), 12, 12)
        for b in self.buttons:
            b.draw(s)

    def on_down(self, pos):
        if super().on_down(pos):
            return True
        if self.debug and TITO_TAP.collidepoint(pos):
            self.app.go(lambda: DebugScene(self.app))
        return True

    def continue_game(self):
        game = self.app.save.get("game")
        if game and game.get("n"):
            self.app.go(lambda: GameScene(self.app, game["n"], restore=game))
        else:
            self.play()

    def play(self):
        self.app.play_level(self.app.save["level"])

    def levels(self):
        self.app.go(lambda: LevelSelectScene(self.app))

    def settings(self):
        self.app.go(lambda: SettingsScene(self.app))

    def quit_game(self):
        self.app.running = False


class LevelSelectScene(Scene):
    """Сетка уровней: открыты пройденные и текущий. Красные — боссы."""

    def __init__(self, app, page=None):
        super().__init__(app)
        self.bg = gradient((24, 20, 56), (6, 6, 16))
        self.bokeh = Bokeh(12)
        top = app.save["level"]
        self.total_pages = (top - 1) // PER_PAGE + 1
        if page is None:
            page = (top - 1) // PER_PAGE
        self.page = min(max(0, page), self.total_pages - 1)
        self.buttons = []
        for i in range(PER_PAGE):
            n = self.page * PER_PAGE + i + 1
            col, row = i % 5, i // 5
            unlocked = n <= top
            color = (200, 70, 110) if n % BOSS_EVERY == 0 else (70, 130, 230)
            self.buttons.append(Button(R(40 + col * 96, 200 + row * 96, 84, 84), str(n),
                                       (lambda nn=n: self.app.play_level(nn)), color, 30,
                                       enabled=unlocked))
        self.buttons.append(Button(R(40, 800, 140, 60), "<", self.prev_page, (90, 90, 120), 30,
                                   enabled=self.page > 0))
        self.buttons.append(Button(R(360, 800, 140, 60), ">", self.next_page, (90, 90, 120), 30,
                                   enabled=self.page < self.total_pages - 1))
        self.buttons.append(Button(R(160, 880, 220, 56), "НАЗАД", self.app.to_menu, (150, 90, 220), 28))

    def prev_page(self):
        self.app.go(lambda: LevelSelectScene(self.app, self.page - 1))

    def next_page(self):
        self.app.go(lambda: LevelSelectScene(self.app, self.page + 1))

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        self.bokeh.draw(s)
        draw_text(s, "ВЫБОР УРОВНЯ", get_font(44, True), (255, 255, 255), 270, 120, "center")
        draw_text(s, f"Страница {self.page + 1} из {self.total_pages}", get_font(20), (190, 200, 230),
                  270, 166, "center")
        for i, b in enumerate(self.buttons[:PER_PAGE]):
            n = self.page * PER_PAGE + i + 1
            if n % BOSS_EVERY == 0 and b.enabled:
                draw_text(s, "БОСС", get_font(13, True), (255, 230, 230), b.rect.centerx,
                          b.rect.bottom - 14, "center")
        super().draw(s)
        draw_text(s, "Тап по открытому уровню — начать", get_font(18), (170, 180, 210), 270, 606, "center")


class SettingsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = gradient((20, 40, 40), (5, 10, 15))
        self.bokeh = Bokeh(10)
        self.confirm = False
        self.sound_btn = Button(R(90, 250, 360, 70), "", self.toggle_sound, (60, 160, 130), 30)
        self.voice_btn = Button(R(90, 336, 360, 70), "", self.toggle_voice, (70, 130, 200), 30)
        self.retry_btn = Button(R(90, 422, 360, 70), "ПЕРЕКАЧАТЬ ОЗВУЧКУ", self.retry_voice,
                                (120, 110, 200), 24)
        self.reset_btn = Button(R(90, 508, 360, 70), "СБРОСИТЬ ПРОГРЕСС", self.reset, (190, 70, 70), 24)
        self.back_btn = Button(R(120, 840, 300, 64), "НАЗАД", self.back, (90, 90, 120), 30)
        self.buttons = [self.sound_btn, self.voice_btn, self.retry_btn, self.reset_btn, self.back_btn]

    def update(self, dt):
        super().update(dt)
        s = self.app.save
        self.sound_btn.text = "ЗВУКИ: " + ("ВКЛ" if s["sound"] else "ВЫКЛ")
        self.voice_btn.text = "ОЗВУЧКА: " + ("ВКЛ" if s["voice"] else "ВЫКЛ")
        self.reset_btn.text = "ТОЧНО СБРОСИТЬ?" if self.confirm else "СБРОСИТЬ ПРОГРЕСС"

    def toggle_sound(self):
        self.app.save["sound"] = not self.app.save["sound"]
        write_save(self.app.save)
        self.confirm = False

    def toggle_voice(self):
        self.app.save["voice"] = not self.app.save["voice"]
        write_save(self.app.save)
        self.confirm = False

    def retry_voice(self):
        self.confirm = False
        self.app.start_voice()

    def reset(self):
        if not self.confirm:
            self.confirm = True
            return
        self.app.save.update({"level": 1, "best": 0, "game": None, "seen": []})
        write_save(self.app.save)
        self.confirm = False
        self.app.to_menu()

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
            return f"Озвучка готова: {st['done']} реплик"
        if state == "offline":
            return "Нет интернета: нажми «Перекачать озвучку»"
        if state == "nogtts":
            return "Не найден gTTS. ПК: pip install gtts. Или положи mp3 в папку voice/"
        return "Нет доступа к папке для озвучки"

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        self.bokeh.draw(s)
        draw_text(s, "НАСТРОЙКИ", get_font(52, True), (255, 255, 255), 270, 150, "center")
        draw_text(s, self.voice_text(), get_font(20), (190, 230, 210), 270, 220, "center")
        super().draw(s)
