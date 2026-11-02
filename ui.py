# -*- coding: utf-8 -*-
"""Общий интерфейс: базовая сцена, кнопки, панели, подписи-чипы, анимированный фон."""
import random

import pygame

from config import BASE_W, BASE_H
from render import R, get_font, draw_text, glow


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

    def on_quit(self):
        pass


def _mix(c, k):
    """k > 0 — светлее, k < 0 — темнее."""
    if k >= 0:
        return tuple(int(v + (255 - v) * k) for v in c)
    return tuple(int(v * (1 + k)) for v in c)


class Button:
    def __init__(self, rect, text, cb, color=(70, 130, 230), font_size=34, enabled=True):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.cb = cb
        self.color = color
        self.font_size = font_size
        self.hover = 0.0
        self.press = 0.0
        self.pressed = False
        self.enabled = enabled

    def update(self, dt, mouse):
        target = 1.0 if self.rect.collidepoint(mouse) else 0.0
        self.hover += (target - self.hover) * min(1.0, dt * 12)
        tp = 1.0 if self.pressed else 0.0
        self.press += (tp - self.press) * min(1.0, dt * 20)

    def draw(self, s):
        base = self.color if self.enabled else (66, 66, 80)
        k = 1 + 0.035 * self.hover - 0.05 * self.press
        r = pygame.Rect(0, 0, int(self.rect.w * k), int(self.rect.h * k))
        r.center = self.rect.center
        pygame.draw.rect(s, _mix(base, -0.5), r.move(0, 7), border_radius=22)
        pygame.draw.rect(s, base, r, border_radius=22)
        pygame.draw.rect(s, _mix(base, 0.3), R(r.x + 10, r.y + 6, r.w - 20, r.h * 0.38), border_radius=16)
        if self.text:
            font = get_font(self.font_size, True)
            draw_text(s, self.text, font, (0, 0, 0), r.centerx + 2, r.centery + 2, "center")
            draw_text(s, self.text, font, (255, 255, 255) if self.enabled else (150, 150, 160),
                      r.centerx, r.centery, "center")


def panel(s, rect, fill=(16, 14, 40), border=(120, 100, 200), radius=22, width=3):
    pygame.draw.rect(s, (4, 4, 10), rect.move(0, 6), border_radius=radius)
    pygame.draw.rect(s, fill, rect, border_radius=radius)
    pygame.draw.rect(s, border, rect, width, border_radius=radius)


def chip_width(text, dot=True):
    return get_font(19, True).size(text)[0] + 28 + (14 if dot else 0)


def chip(s, x, y, text, color, dot=True, h=30):
    w = chip_width(text, dot)
    rect = R(x, y, w, h)
    pygame.draw.rect(s, (12, 10, 28), rect, border_radius=h // 2)
    pygame.draw.rect(s, color, rect, 2, border_radius=h // 2)
    tx = x + 14
    if dot:
        pygame.draw.circle(s, color, (int(x + 16), int(y + h // 2)), 6)
        tx = x + 28
    draw_text(s, text, get_font(19, True), (245, 245, 255), tx, y + h // 2, "midleft")
    return w


def chips_centered(s, y, items, center_x=270, gap=10):
    widths = [chip_width(t, dot=False) for t, _ in items]
    x = center_x - (sum(widths) + gap * (len(items) - 1)) / 2
    for (text, col), w in zip(items, widths):
        chip(s, int(x), y, text, col, dot=False)
        x += w + gap


class Bokeh:
    """Плавающие световые пятна на фоне."""
    PALETTE = ((255, 190, 90), (110, 230, 255), (200, 150, 255), (120, 255, 170))

    def __init__(self, n=22, seed=None):
        rng = random.Random(seed)
        self.items = [[rng.uniform(0, BASE_W), rng.uniform(0, BASE_H), rng.uniform(8, 24),
                       rng.uniform(12, 30), rng.choice(self.PALETTE)] for _ in range(n)]

    def update(self, dt):
        for it in self.items:
            it[1] -= it[3] * dt
            if it[1] < -40:
                it[1] = BASE_H + 40
                it[0] = random.uniform(0, BASE_W)

    def draw(self, s):
        for x, y, r, _, col in self.items:
            s.blit(glow(int(r), col), (int(x - r), int(y - r)))
