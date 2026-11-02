# -*- coding: utf-8 -*-
"""Рисунки новых объектов: особые фишки, таймер, препятствия, боссы, реквизит катсцен."""
import math

import pygame

from config import CELL, GEMS
from logic import Star, Bomb, Magnet, Lightning, Timer, Monster, is_gem
from render import (R, P, glow, get_font, draw_text, draw_gem, draw_star_piece, draw_bomb,
                    draw_monster, draw_mur, make_obstacle_surfs)

_cache = {}


def _cached(key, build):
    if key not in _cache:
        _cache[key] = build()
    return _cache[key]


def _pt(x, y):
    return (int(x), int(y))


def _halo(s, x, y, rad, col):
    g = glow(max(2, int(rad)), col)
    s.blit(g, (int(x - rad), int(y - rad)))


# ---------------------------------------------------------------- особые фишки
def draw_magnet(s, x, y, r, t):
    rr = r * (1 + 0.05 * math.sin(t * 7))
    _halo(s, x, y, rr * 1.8, (120, 200, 255))
    cx, cy = x, y - rr * 0.15
    w = max(3, int(rr * 0.42))
    pygame.draw.arc(s, (70, 70, 85), R(cx - rr, cy - rr, 2 * rr, 2 * rr), 0, math.pi, w)
    pygame.draw.rect(s, (70, 70, 85), R(cx - rr - w / 2, cy, w, rr * 0.7))
    pygame.draw.rect(s, (70, 70, 85), R(cx + rr - w / 2, cy, w, rr * 0.7))
    pygame.draw.circle(s, (235, 70, 80), _pt(cx + rr, cy + rr * 0.7), max(2, int(w * 0.6)))
    pygame.draw.circle(s, (75, 135, 240), _pt(cx - rr, cy + rr * 0.7), max(2, int(w * 0.6)))


def draw_lightning(s, x, y, r, t):
    rr = r * (1 + 0.08 * math.sin(t * 12))
    _halo(s, x, y, rr * 1.7, (255, 240, 120))
    pts = [(x - rr * 0.25, y - rr * 0.9), (x + rr * 0.35, y - rr * 0.15), (x + rr * 0.02, y - rr * 0.05),
           (x + rr * 0.3, y + rr * 0.9), (x - rr * 0.35, y + rr * 0.1), (x - rr * 0.02, y + rr * 0.02)]
    pygame.draw.polygon(s, (255, 250, 200), P(pts))
    pygame.draw.polygon(s, (255, 200, 60), P(pts), 2)


def draw_timer(s, x, y, r, t, left):
    danger = left <= 2
    rr = r * (1 + (0.08 * math.sin(t * 14) if danger else 0.0))
    _halo(s, x, y, rr * 1.6, (255, 70, 60) if danger else (255, 150, 80))
    pygame.draw.circle(s, (30, 26, 32), _pt(x, y + 2), int(rr))
    pygame.draw.circle(s, (120, 110, 120), _pt(x, y), int(rr), 3)
    pygame.draw.circle(s, (255, 210, 80), _pt(x + rr * 0.55, y - rr * 0.8), max(2, int(rr * 0.16)))
    draw_text(s, str(left), get_font(max(14, int(rr * 1.05)), True), (255, 255, 255), x, y, "center")


def draw_any(s, v, x, y, r, t):
    """Рисует любой объект поля: фишку, особую фишку, таймер или монстра."""
    if is_gem(v):
        draw_gem(s, v, x, y, r)
    elif isinstance(v, Star):
        draw_star_piece(s, x, y, r, t)
    elif isinstance(v, Bomb):
        draw_bomb(s, x, y, r, t)
    elif isinstance(v, Magnet):
        draw_magnet(s, x, y, r, t)
    elif isinstance(v, Lightning):
        draw_lightning(s, x, y, r, t)
    elif isinstance(v, Timer):
        draw_timer(s, x, y, r, t, v.left)
    elif isinstance(v, Monster):
        draw_monster(s, x, y, r, v.hp, v.species, t, v.flash)


# ---------------------------------------------------------------- препятствия
def _scaled(key, size):
    base = _cached("obs", make_obstacle_surfs)[key]
    if base.get_width() == size:
        return base
    return _cached(("sc", key, size), lambda: pygame.transform.smoothscale(base, (size, size)))


def _build_web(hp, size):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    n = 4 + 2 * hp
    for i in range(n):
        a = math.tau * i / n
        pygame.draw.line(s, (235, 240, 255, 200), _pt(c, c),
                         _pt(c + math.cos(a) * size * 0.5, c + math.sin(a) * size * 0.5), 2)
    for k in range(1, hp + 2):
        pygame.draw.circle(s, (235, 240, 255, 170), _pt(c, c), max(2, int(size * 0.12 * k)), 1)
    return s


def _build_chain(hp, size):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    m = size * 0.12
    diags = [((m, m), (size - m, size - m)), ((size - m, m), (m, size - m))][:hp]
    for (x0, y0), (x1, y1) in diags:
        for i in range(5):
            f = i / 4
            pygame.draw.circle(s, (165, 170, 185, 255),
                               _pt(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f), max(3, int(size * 0.09)), 3)
    return s


def _build_stone(hp, size):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pts = [(0.1, 0.15), (0.5, 0.02), (0.92, 0.12), (0.98, 0.55), (0.85, 0.95), (0.4, 0.98), (0.02, 0.85), (0.0, 0.45)]
    poly = P([(x * size, y * size) for x, y in pts])
    pygame.draw.polygon(s, (120, 118, 128, 255), poly)
    pygame.draw.polygon(s, (70, 68, 80, 255), poly, 3)
    for k in range(3 - hp):
        pygame.draw.lines(s, (30, 28, 36, 255), False,
                          P([(size * (0.3 + 0.2 * k), size * 0.2), (size * (0.45 + 0.2 * k), size * 0.5),
                             (size * (0.35 + 0.2 * k), size * 0.8)]), 2)
    return s


def _slime(s, x, y, size, t):
    base = pygame.Surface((size, size), pygame.SRCALPHA)
    col = (110, 230, 90, 200)
    pygame.draw.ellipse(base, col, R(size * 0.08, size * 0.2, size * 0.84, size * 0.66))
    for i in range(3):
        dx = size * (0.25 + 0.25 * i)
        drip = size * (0.12 + 0.1 * abs(math.sin(t * 3 + i * 1.7)))
        pygame.draw.rect(base, col, R(dx - size * 0.06, size * 0.6, size * 0.12, drip + size * 0.1), border_radius=4)
        pygame.draw.circle(base, col, _pt(dx, size * 0.6 + drip + size * 0.1), max(2, int(size * 0.07)))
    pygame.draw.circle(base, (230, 255, 220, 230), _pt(size * 0.36, size * 0.4), max(2, int(size * 0.07)))
    s.blit(base, (int(x), int(y)))


def draw_obstacle(s, kind, hp, x, y, t, size=CELL - 8):
    """(x, y) — левый верхний угол клетки, size — сторона квадрата."""
    x, y = int(x), int(y)
    if kind == "ice":
        s.blit(_scaled("ice", size), (x, y))
    elif kind == "brick":
        s.blit(_scaled("brick2" if hp >= 2 else "brick1", size), (x, y))
    elif kind == "web":
        s.blit(_cached(("web", min(hp, 3), size), lambda: _build_web(min(hp, 3), size)), (x, y))
    elif kind == "chain":
        s.blit(_cached(("chain", min(hp, 2), size), lambda: _build_chain(min(hp, 2), size)), (x, y))
    elif kind == "stone":
        s.blit(_cached(("stone", min(hp, 3), size), lambda: _build_stone(min(hp, 3), size)), (x, y))
    elif kind == "slime":
        _slime(s, x, y, size, t)


# ---------------------------------------------------------------- боссы и реквизит
def draw_boss(s, kind, cx, bottom, size, t, talk=False):
    """kind 0 — Мурзик-гигант, 1..5 — монстры-боссы (слизень, мышь, призрак, паук, циклоп)."""
    if kind == 0:
        draw_mur(s, cx, bottom, 280 * size, t, talk=talk)
    else:
        r = 92 * size
        draw_monster(s, cx, bottom - r * 1.2, r, 3, kind - 1, t, 0.0)


def draw_prop(s, name, cx, cy, size, t):
    """Реквизит для катсцен: предметы, препятствия и механики."""
    r = size * 0.42
    if name == "gem":
        draw_gem(s, int(t) % len(GEMS), cx, cy, r)
    elif name == "monster":
        draw_monster(s, cx, cy, r * 0.85, 3, 0, t)
    elif name == "star":
        draw_star_piece(s, cx, cy, r, t)
    elif name == "bomb":
        draw_bomb(s, cx, cy, r, t)
    elif name == "magnet":
        draw_magnet(s, cx, cy, r, t)
    elif name == "lightning":
        draw_lightning(s, cx, cy, r, t)
    elif name == "timer":
        draw_timer(s, cx, cy, r, t, 3)
    elif name in ("ice", "brick", "web", "chain", "stone", "slime"):
        sz = int(size * 0.8)
        hp = {"brick": 2, "chain": 2, "stone": 3}.get(name, 1)
        draw_obstacle(s, name, hp, cx - sz / 2, cy - sz / 2, t, sz)
    elif name == "fog":
        for i in range(6):
            fx = cx + math.cos(t + i) * size * 0.25
            fy = cy + math.sin(t * 0.7 + i) * size * 0.2
            _halo(s, fx, fy, size * 0.22, (200, 200, 220))
    elif name == "gravity":
        off = math.sin(t * 4) * 8
        for dx in (-r * 0.45, r * 0.45):
            col = (255, 220, 120)
            pygame.draw.polygon(s, col, P([(cx + dx, cy - r - off), (cx + dx + r * 0.35, cy - r * 0.2 - off),
                                           (cx + dx - r * 0.35, cy - r * 0.2 - off)]))
            pygame.draw.rect(s, col, R(cx + dx - r * 0.12, cy - r * 0.2 - off, r * 0.24, r * 1.0))
    elif name == "shuffle":
        for k in range(2):
            ang = (t * 2 + k * math.pi) % math.tau
            pygame.draw.arc(s, (120, 255, 190), R(cx - r, cy - r, 2 * r, 2 * r), ang, ang + 2.2, 6)
