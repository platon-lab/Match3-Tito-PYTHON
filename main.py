# -*- coding: utf-8 -*-
"""Точка входа: окно, переходы между экранами, катсцены, озвучка, главный цикл.
Если игра падает с ошибкой, текст показывается на экране и пишется в crash.log."""
import os
import threading
import traceback

import pygame

from config import IS_ANDROID, BASE_W, BASE_H, FPS, DATA_DIR, load_save, write_save, BOSS_EVERY
from audio import Audio, voice_worker
from render import load_portrait, get_font, draw_text, wrap_text
from story import all_voice_texts, new_mechanics, level_beats, boss_beats
from config import make_level
from scenes import IntroScene
from menu import MenuScene
from game import GameScene
from boss import BossScene
from cutscenes import CutsceneScene

BACK_KEYS = (pygame.K_ESCAPE, getattr(pygame, "K_AC_BACK", -999))


class TitoApp:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        if IS_ANDROID:
            self.screen = pygame.display.set_mode((0, 0))
        else:
            self.screen = pygame.display.set_mode((BASE_W, BASE_H), pygame.RESIZABLE)
        pygame.display.set_caption("Тито: три в ряд")
        self.canvas = pygame.Surface((BASE_W, BASE_H))
        self.clock = pygame.time.Clock()

        self.save = load_save()
        self.audio = Audio(self.save)
        load_portrait()

        self.voice_status = {"state": "idle", "done": 0, "total": 0}
        self.start_voice()

        self.running = True
        self.debug_play = False     # True, когда уровень запущен из дебаг-меню: прогресс не меняем
        self.crash_text = None
        self.scale = 1.0
        self.ox = self.oy = 0
        self.dsize = (BASE_W, BASE_H)
        self._layout()

        self.fade_surf = pygame.Surface((BASE_W, BASE_H))
        self.fade_surf.fill((0, 0, 0))
        self.fade_a = 255.0
        self.fade_dir = -1
        self.pending = None

        if self.save.get("intro_done"):
            self.scene = MenuScene(self)
        else:
            self.scene = IntroScene(self, self.intro_finished)

    # ---------- озвучка
    def start_voice(self):
        st = self.voice_status
        if st["state"] == "loading":
            return
        texts = all_voice_texts()
        st.update(state="idle", done=0, total=len(texts))
        threading.Thread(target=voice_worker, args=(texts, st), daemon=True).start()

    # ---------- переходы между экранами
    def go(self, factory):
        if self.pending is None and self.fade_dir == 0:
            self.pending = factory
            self.fade_dir = 1

    def intro_finished(self):
        self.save["intro_done"] = True
        write_save(self.save)
        self.to_menu()

    def to_menu(self):
        self.debug_play = False
        self.go(lambda: MenuScene(self))

    def play_level(self, n):
        """Перед боссом и перед уровнем с новыми механиками, главой или тяжёлым уровнем — катсцена."""
        if n % BOSS_EVERY == 0:
            self._cutscene(boss_beats(n), lambda: BossScene(self, n))
            return
        cfg = make_level(n)
        new = new_mechanics(cfg, self.save.get("seen", []))
        beats = level_beats(cfg, new)
        factory = lambda: GameScene(self, n)
        if beats:
            self._cutscene(beats, factory, mark=new)
        else:
            self.go(factory)

    def _cutscene(self, beats, factory, mark=()):
        def done():
            if mark and not self.debug_play:
                self.save["seen"] = sorted(set(self.save.get("seen", [])) | set(mark))
                write_save(self.save)
            self.go(factory)
        self.go(lambda: CutsceneScene(self, beats, done))

    def _update_fade(self, dt):
        if self.fade_dir == 1:
            self.fade_a = min(255.0, self.fade_a + dt * 900)
            if self.fade_a >= 255:
                self.scene = self.pending()
                self.pending = None
                self.fade_dir = -1
        elif self.fade_dir == -1:
            self.fade_a = max(0.0, self.fade_a - dt * 700)
            if self.fade_a <= 0:
                self.fade_dir = 0

    # ---------- масштаб под любой экран
    def _layout(self):
        sw, sh = self.screen.get_size()
        self.scale = min(sw / BASE_W, sh / BASE_H)
        self.dsize = (max(1, int(BASE_W * self.scale)), max(1, int(BASE_H * self.scale)))
        self.ox = (sw - self.dsize[0]) // 2
        self.oy = (sh - self.dsize[1]) // 2

    def to_logical(self, pos):
        return ((pos[0] - self.ox) / self.scale, (pos[1] - self.oy) / self.scale)

    # ---------- рисование
    def _render(self):
        self.scene.draw(self.canvas)
        if self.fade_a > 0:
            self.fade_surf.set_alpha(int(self.fade_a))
            self.canvas.blit(self.fade_surf, (0, 0))

    def _present(self):
        self.screen.fill((0, 0, 0))
        self.screen.blit(pygame.transform.scale(self.canvas, self.dsize), (self.ox, self.oy))
        pygame.display.flip()

    # ---------- события и шаг игры
    def _handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.VIDEORESIZE and not IS_ANDROID:
                self.screen = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
            elif self.fade_dir != 0:
                continue
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.scene.on_down(self.to_logical(ev.pos))
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                self.scene.on_up(self.to_logical(ev.pos))
            elif ev.type == pygame.MOUSEMOTION:
                self.scene.on_motion(self.to_logical(ev.pos))
            elif ev.type == pygame.KEYDOWN and ev.key in BACK_KEYS:
                self.scene.on_back()

    def _step(self, dt):
        self._handle_events()
        self._layout()
        self.scene.update(dt)
        self._update_fade(dt)
        self._render()

    # ---------- ошибки
    def _report_crash(self, text):
        self.crash_text = text
        try:
            with open(os.path.join(DATA_DIR, "crash.log"), "w", encoding="utf-8") as f:
                f.write(text)
        except Exception:
            pass

    def _draw_crash(self):
        self.canvas.fill((40, 0, 0))
        draw_text(self.canvas, "Игра упала. Текст ошибки:", get_font(22, True),
                  (255, 220, 120), 16, 16)
        draw_text(self.canvas, "Он также записан в crash.log", get_font(16), (230, 200, 200), 16, 46)
        font = get_font(15)
        y = 76
        for line in self.crash_text.strip().splitlines()[-40:]:
            for part in wrap_text(line, font, BASE_W - 30) or [""]:
                if y > BASE_H - 20:
                    return
                draw_text(self.canvas, part, font, (255, 235, 235), 16, y)
                y += 17

    # ---------- главный цикл
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            if self.crash_text is None:
                try:
                    self._step(dt)
                except Exception:
                    self._report_crash(traceback.format_exc())
            if self.crash_text is not None:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        self.running = False
                self._draw_crash()
            self._present()

        try:
            self.scene.on_quit()
        except Exception:
            pass
        self.audio.stop_voice()
        pygame.quit()


if __name__ == "__main__":
    TitoApp().run()
