# -*- coding: utf-8 -*-
"""Точка входа: окно, переходы между экранами, главный цикл.
Запуск на ПК:  python main.py
Запуск на телефоне: собирается в APK через GitHub Actions (buildozer)."""
import threading

import pygame

from config import IS_ANDROID, BASE_W, BASE_H, FPS, INTRO_TEXTS, load_save, write_save
from audio import Audio, voice_worker
from render import load_portrait
from scenes import MenuScene, IntroScene, GameScene
from boss import BossScene

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

        self.voice_status = {"state": "idle", "done": 0, "total": len(INTRO_TEXTS)}
        threading.Thread(target=voice_worker, args=(INTRO_TEXTS, self.voice_status),
                         daemon=True).start()

        self.tito_taps = 0
        self.running = True
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

    # ---------- переходы
    def go(self, factory):
        if self.pending is None and self.fade_dir == 0:
            self.pending = factory
            self.fade_dir = 1

    def intro_finished(self):
        self.save["intro_done"] = True
        write_save(self.save)
        self.to_menu()

    def to_menu(self):
        self.go(lambda: MenuScene(self))

    def play_level(self, n):
        if n % 100 == 0:
            self.play_boss(n)
        else:
            self.go(lambda: GameScene(self, n))

    def play_boss(self, n):
        self.go(lambda: BossScene(self, n))

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

    def _draw(self):
        self.scene.draw(self.canvas)
        if self.fade_a > 0:
            self.fade_surf.set_alpha(int(self.fade_a))
            self.canvas.blit(self.fade_surf, (0, 0))
        self.screen.fill((0, 0, 0))
        scaled = pygame.transform.scale(self.canvas, self.dsize)
        self.screen.blit(scaled, (self.ox, self.oy))

    # ---------- главный цикл
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
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
            self._layout()
            self.scene.update(dt)
            self._update_fade(dt)
            self._draw()
            pygame.display.flip()
        self.audio.stop_voice()
        pygame.quit()


if __name__ == "__main__":
    TitoApp().run()
