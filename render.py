# -*- coding: utf-8 -*-
"""Всё, что рисуется: фишки, звёзды, монстры, Тито, Мурзик, текст, фоны."""
import math
import random
import os

import pygame

from config import BASE_W, BASE_H, GEMS, MONSTER_COLORS, PHOTO_FILE
from logic import is_gem, Star, Monster

_font_cache = {}
_grad_cache = {}
_glow_cache = {}
_portrait = {"src": None, "cache": {}}


# ---------------------------------------------------------------- помощники
def get_font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        try:
            f = pygame.font.Font(pygame.font.get_default_font(), size)
        except Exception:
            f = pygame.font.Font(None, size)
        f.set_bold(bold)
        _font_cache[key] = f
    return _font_cache[key]


def draw_text(surf, text, font, color, x, y, anchor="topleft"):
    img = font.render(text, True, color)
    rect = img.get_rect(**{anchor: (int(x), int(y))})
    surf.blit(img, rect)
    return rect


def wrap_text(text, font, width):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if font.size(test)[0] <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def R(x, y, w, h):
    return pygame.Rect(int(x), int(y), int(max(1, w)), int(max(1, h)))


def P(points):
    return [(int(x), int(y)) for x, y in points]


def gradient(top, bottom):
    key = (top, bottom)
    if key not in _grad_cache:
        s = pygame.Surface((BASE_W, BASE_H))
        for y in range(BASE_H):
            t = y / (BASE_H - 1)
            col = tuple(int(lerp(top[i], bottom[i], t)) for i in range(3))
            pygame.draw.line(s, col, (0, y), (BASE_W, y))
        _grad_cache[key] = s
    return _grad_cache[key]


def glow(radius, color):
    key = (radius, color)
    if key not in _glow_cache:
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for i in range(radius, 0, -3):
            a = int(110 * (1 - i / radius) ** 1.6)
            pygame.draw.circle(s, (*color, a), (radius, radius), i)
        _glow_cache[key] = s
    return _glow_cache[key]


def make_stars(n=60):
    return [(random.uniform(0, BASE_W), random.uniform(0, BASE_H),
             random.uniform(0, 6.28), random.choice((1, 1, 2))) for _ in range(n)]


def star_field(s, stars, t):
    for x, y, ph, size in stars:
        b = 0.5 + 0.5 * math.sin(t * 2 + ph)
        v = int(120 + 135 * b)
        pygame.draw.circle(s, (v, v, min(255, v + 20)), (int(x), int(y)), size)


def load_portrait():
    """Фото Тито с убранным белым фоном (если файл tito.jpg рядом)."""
    if not PHOTO_FILE or not __import__("os").path.exists(PHOTO_FILE):
        return
    try:
        img = pygame.image.load(PHOTO_FILE)
        w, h = img.get_size()
        nh = 260
        nw = max(1, int(w * nh / h))
        small = pygame.transform.smoothscale(img, (nw, nh))
        out = pygame.Surface((nw, nh), pygame.SRCALPHA)
        for x in range(nw):
            for y in range(nh):
                c = small.get_at((x, y))
                if c.r > 225 and c.g > 225 and c.b > 225:
                    continue
                out.set_at((x, y), (c.r, c.g, c.b, 255))
        _portrait["src"] = out
    except Exception:
        _portrait["src"] = None


def portrait_scaled(height):
    src = _portrait["src"]
    if src is None:
        return None
    height = int(height)
    if height not in _portrait["cache"]:
        w = max(1, int(src.get_width() * height / src.get_height()))
        _portrait["cache"][height] = pygame.transform.smoothscale(src, (w, height))
    return _portrait["cache"][height]


# ---------------------------------------------------------------- фишки
def draw_gem(surf, kind, cx, cy, r):
    if r < 2:
        return
    color, shape = GEMS[kind]
    dark = tuple(max(0, c - 80) for c in color)
    light = tuple(min(255, c + 90) for c in color)
    sh = max(2, int(r * 0.14))
    if shape == "circle":
        pygame.draw.circle(surf, dark, (int(cx), int(cy + sh)), int(r))
        pygame.draw.circle(surf, color, (int(cx), int(cy)), int(r))
        pygame.draw.circle(surf, light, (int(cx - r * 0.35), int(cy - r * 0.35)), max(2, int(r * 0.25)))
    elif shape == "square":
        rect = R(cx - r, cy - r, 2 * r, 2 * r)
        br = max(2, int(r * 0.4))
        pygame.draw.rect(surf, dark, rect.move(0, sh), border_radius=br)
        pygame.draw.rect(surf, color, rect, border_radius=br)
        pygame.draw.rect(surf, light, R(cx - r * 0.6, cy - r * 0.7, r * 0.7, r * 0.25), border_radius=3)
    else:
        pts = _polygon_for(shape, cx, cy, r)
        pygame.draw.polygon(surf, dark, P([(x, y + sh) for x, y in pts]))
        pygame.draw.polygon(surf, color, P(pts))
        pygame.draw.circle(surf, light, (int(cx - r * 0.35), int(cy - r * 0.2)), max(2, int(r * 0.18)))


def _polygon_for(shape, cx, cy, r):
    if shape == "triangle":
        return [(cx, cy - r), (cx + r * 0.95, cy + r * 0.75), (cx - r * 0.95, cy + r * 0.75)]
    if shape == "diamond":
        return [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    if shape == "hex":
        return [(cx + r * math.cos(math.radians(60 * i + 30)),
                 cy + r * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.45
        ang = math.radians(-90 + 36 * i)
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


def draw_star_piece(s, x, y, r, t):
    """Антиматерия: пульсирующая фиолетовая звезда с ореолом."""
    pulse = 1 + 0.08 * math.sin(t * 6)
    rr = r * pulse
    g = glow(int(rr * 1.9), (170, 110, 255))
    s.blit(g, (int(x - rr * 1.9), int(y - rr * 1.9)))
    for scale, col in ((1.0, (200, 150, 255)), (0.55, (255, 245, 255))):
        pts = []
        for i in range(10):
            rad = (rr if i % 2 == 0 else rr * 0.45) * scale
            ang = -math.pi / 2 + i * math.pi / 5 + t * 0.6
            pts.append((x + rad * math.cos(ang), y + rad * math.sin(ang)))
        pygame.draw.polygon(s, col, P(pts))


def draw_monster(s, x, y, r, hp, species, t, flash=0.0):
    col = MONSTER_COLORS[species % len(MONSTER_COLORS)]
    dark = tuple(max(0, c - 70) for c in col)
    body = (255, 255, 255) if flash > 0.15 else col
    pts = []
    for i in range(16):
        a = i / 16 * math.tau
        rr = r * (1 + 0.07 * math.sin(t * 5 + i * 1.3))
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a) * 0.9))
    pygame.draw.polygon(s, dark, P([(px, py + 4) for px, py in pts]))
    pygame.draw.polygon(s, body, P(pts))
    for ex in (-0.3, 0.3):
        cx_, cy_ = x + ex * r, y - 0.15 * r
        pygame.draw.circle(s, (255, 255, 255), (int(cx_), int(cy_)), max(2, int(r * 0.28)))
        pygame.draw.circle(s, (20, 15, 25), (int(cx_ + ex * 0.2 * r), int(cy_ + 2)), max(1, int(r * 0.13)))
    pygame.draw.line(s, dark, (int(x - 0.5 * r), int(y - 0.45 * r)), (int(x - 0.15 * r), int(y - 0.33 * r)), 3)
    pygame.draw.line(s, dark, (int(x + 0.5 * r), int(y - 0.45 * r)), (int(x + 0.15 * r), int(y - 0.33 * r)), 3)
    for i in range(3):
        px_ = x - r * 0.5 + i * r * 0.5
        pygame.draw.circle(s, (255, 80, 80) if i < hp else (55, 55, 60), (int(px_), int(y - r - 9)), 5)


def draw_piece(s, v, x, y, r, t):
    if is_gem(v):
        draw_gem(s, v, x, y, r)
    elif isinstance(v, Star):
        draw_star_piece(s, x, y, r, t)
    elif isinstance(v, Monster):
        draw_monster(s, x, y, r, v.hp, v.species, t, v.flash)


def draw_bone(s, x, y, length=34, col=(255, 210, 90)):
    h = 9
    pygame.draw.rect(s, col, R(x - length / 2, y - h / 2, length, h), border_radius=4)
    for ex in (-length / 2, length / 2):
        pygame.draw.circle(s, col, (int(x + ex), int(y - 4)), 6)
        pygame.draw.circle(s, col, (int(x + ex), int(y + 4)), 6)


def draw_heart(s, x, y, size, col=(235, 60, 90)):
    pygame.draw.circle(s, col, (int(x - size * 0.5), int(y)), int(size * 0.55))
    pygame.draw.circle(s, col, (int(x + size * 0.5), int(y)), int(size * 0.55))
    pygame.draw.polygon(s, col, P([(x - size, y + size * 0.1), (x + size, y + size * 0.1), (x, y + size * 1.2)]))


# ---------------------------------------------------------------- Тито
def draw_tito(s, cx, bottom, h, t=0.0, talk=False, walk=0.0, dirn=1,
              bag=False, bag_open=False, blink=False, sad=False):
    """Тито: чёрный пёс с синим ошейником. cx/bottom — точка под лапами.
    dirn=1 смотрит вправо, dirn=-1 влево. walk>0 — идёт."""
    k = h / 240.0

    def X(dx):
        return cx + dirn * dx * k

    def Y(dy):
        return bottom + dy * k

    def ell(dx, dy, w, hh, col):
        pygame.draw.ellipse(s, col, R(X(dx) - w * k / 2, Y(dy) - hh * k / 2, w * k, hh * k))

    def poly(pts, col):
        pygame.draw.polygon(s, col, [(int(X(a)), int(Y(b))) for a, b in pts])

    def circ(dx, dy, rad, col):
        pygame.draw.circle(s, col, (int(X(dx)), int(Y(dy))), max(1, int(rad * k)))

    def line(pts, col, w):
        pygame.draw.lines(s, col, False, [(int(X(a)), int(Y(b))) for a, b in pts], max(1, int(w * k)))

    BLACK = (27, 27, 34)
    HI = (58, 58, 70)
    SH = (10, 10, 13)
    MUZ = (46, 46, 56)

    def leg(dx, ph):
        sw = math.sin(walk + ph) if walk else 0.0
        lift = max(0.0, math.cos(walk + ph)) * 7 if walk else 0.0
        fx = dx + sw * 10
        pygame.draw.rect(s, BLACK, R(X(fx) - 12 * k, Y(-74), 24 * k, (66 - lift) * k),
                         border_radius=max(2, int(10 * k)))
        ell(fx + 6, -10 - lift, 36, 18, BLACK)

    # шадоу под лапами
    ell(0, 2, 170, 14, (15, 15, 18))
    # хвост (за телом)
    wag = math.sin(t * 9) * 8 if walk else math.sin(t * 3) * 4
    line([(-70, -122), (-96, -128), (-108, -150 + wag)], BLACK, 13)
    circ(-108, -150 + wag, 6, BLACK)
    # задние лапы
    leg(-40, 0.0)
    leg(-16, math.pi)
    # тело
    ell(0, -100, 150, 108, BLACK)
    ell(-6, -134, 96, 24, HI)
    ell(-2, -60, 124, 18, SH)
    # передние лапы и грудь
    leg(34, math.pi)
    leg(56, 0.0)
    ell(34, -98, 70, 96, BLACK)
    # рюкзак
    if bag:
        poly([(-64, -176), (-8, -176), (-8, -116), (-64, -116)], (150, 72, 46))
        poly([(-64, -176), (-8, -176), (-8, -168), (-64, -168)], (110, 48, 30))
        circ(-36, -146, 5, (250, 210, 60))
        if bag_open:
            poly([(-64, -176), (-8, -176), (-36, -204)], (120, 55, 35))
    # заднее ухо
    poly([(54, -186), (74, -190), (70, -256), (50, -244)], SH)
    # голова
    circ(62, -160, 50, BLACK)
    # переднее ухо
    poly([(30, -190), (56, -198), (44, -262), (18, -240)], BLACK)
    poly([(34, -196), (50, -200), (42, -248), (25, -234)], (48, 48, 58))
    # морда и нос
    ell(102, -146, 60, 40, MUZ)
    ell(128, -158, 22, 16, (12, 12, 14))
    circ(133, -163, 3, (140, 140, 150))
    # рот
    if talk and math.sin(t * 16) > 0:
        ell(108, -124, 24, 16, (80, 18, 26))
        ell(112, -118, 12, 7, (230, 110, 130))
    else:
        line([(96, -128), (108, -120), (120, -128)], (12, 12, 14), 3)
    # глаза
    eh = 2 if blink else 20
    ell(56, -180, 14, eh * 0.8, (230, 230, 230))
    ell(80, -174, 20, eh, (238, 238, 238))
    if not blink:
        circ(58, -179, 5, (22, 16, 10))
        circ(84, -172, 7, (22, 16, 10))
        circ(86, -175, 2.5, (255, 255, 255))
    if sad:
        line([(70, -198), (90, -190)], (12, 12, 14), 3)
    # ошейник с жетоном
    poly([(14, -150), (46, -118), (48, -102), (16, -134)], (30, 50, 110))
    line([(16, -142), (47, -110)], (250, 210, 60), 3)
    circ(38, -100, 6, (250, 210, 60))


def draw_portrait(s, cx, bottom, h, t=0.0, blink=False, talk=False):
    """Фото Тито, если оно есть, иначе нарисованный Тито. С золотым ореолом."""
    g = glow(int(h * 0.6), (255, 200, 90))
    s.blit(g, (int(cx - h * 0.6), int(bottom - h * 0.5 - h * 0.6)))
    img = portrait_scaled(h)
    if img is not None:
        s.blit(img, img.get_rect(midbottom=(int(cx), int(bottom))))
    else:
        draw_tito(s, cx, bottom, h, t, talk=talk, blink=blink)


def draw_mur(s, cx, bottom, h, t=0.0, talk=False):
    """Мурзик (для босса — огромный, с короной)."""
    k = h / 245.0
    cy = bottom - 115 * k
    fur = (125, 115, 160)
    dark = (85, 76, 118)
    pink = (240, 150, 170)
    tail = [(cx + 50 * k + i * 7 * k, cy + 88 * k - i * 6 * k + math.sin(t * 3 + i * 0.7) * 6 * k)
            for i in range(9)]
    pygame.draw.lines(s, dark, False, P(tail), max(2, int(8 * k)))
    pygame.draw.ellipse(s, fur, R(cx - 55 * k, cy - 5 * k, 110 * k, 115 * k))
    pygame.draw.polygon(s, fur, P([(cx - 42 * k, cy - 60 * k), (cx - 52 * k, cy - 122 * k), (cx - 8 * k, cy - 80 * k)]))
    pygame.draw.polygon(s, fur, P([(cx + 42 * k, cy - 60 * k), (cx + 52 * k, cy - 122 * k), (cx + 8 * k, cy - 80 * k)]))
    pygame.draw.polygon(s, pink, P([(cx - 38 * k, cy - 66 * k), (cx - 46 * k, cy - 110 * k), (cx - 16 * k, cy - 82 * k)]))
    pygame.draw.polygon(s, pink, P([(cx + 38 * k, cy - 66 * k), (cx + 46 * k, cy - 110 * k), (cx + 16 * k, cy - 82 * k)]))
    pygame.draw.circle(s, fur, (int(cx), int(cy - 45 * k)), int(48 * k))
    crown = [(-26, -88), (-26, -106), (-13, -96), (0, -110), (13, -96), (26, -106), (26, -88)]
    pygame.draw.polygon(s, (255, 200, 60), P([(cx + dx * k, cy + dy * k) for dx, dy in crown]))
    for sx in (-1, 1):
        ex, ey = cx + sx * 18 * k, cy - 50 * k
        pygame.draw.ellipse(s, (250, 220, 60), R(ex - 11 * k, ey - 7 * k, 22 * k, 14 * k))
        pygame.draw.ellipse(s, (20, 20, 20), R(ex - 2 * k, ey - 7 * k, 4 * k, 14 * k))
    pygame.draw.polygon(s, pink, P([(cx - 5 * k, cy - 31 * k), (cx + 5 * k, cy - 31 * k), (cx, cy - 25 * k)]))
    for sx in (-1, 1):
        for dy in (-3, 3):
            pygame.draw.line(s, (235, 235, 245), (int(cx + sx * 20 * k), int(cy - 26 * k)),
                             (int(cx + sx * 66 * k), int(cy - 26 * k + dy * k)), max(1, int(2 * k)))
    if talk and math.sin(t * 16) > 0:
        pygame.draw.ellipse(s, (120, 40, 60), R(cx - 10 * k, cy - 22 * k, 20 * k, 12 * k))
    else:
        pygame.draw.arc(s, dark, R(cx - 10 * k, cy - 24 * k, 20 * k, 12 * k),
                        math.pi, 2 * math.pi, max(1, int(2 * k)))


# ---------------------------------------------------------------- HUD
def chip_width(text, icon=None):
    font = get_font(20, True)
    return font.size(text)[0] + 24 + (26 if icon is not None else 0)


def draw_chip(s, x, y, text, color, icon=None, h=36):
    w = chip_width(text, icon)
    rect = R(x, y, w, h)
    pygame.draw.rect(s, tuple(int(c * 0.3) for c in color), rect, border_radius=h // 2)
    pygame.draw.rect(s, color, rect, 2, border_radius=h // 2)
    tx = x + 12
    if icon is not None:
        if isinstance(icon, int):
            draw_gem(s, icon, x + 20, y + h // 2, 10)
        else:
            pygame.draw.rect(s, (200, 240, 255), R(x + 14, y + h // 2 - 6, 12, 12), border_radius=3)
        tx = x + 34
    draw_text(s, text, get_font(20, True), (245, 245, 255), tx, y + h // 2, "midleft")
    return w


def make_ice_surf():
    s = pygame.Surface((CELL_ICE - 8, CELL_ICE - 8), pygame.SRCALPHA)
    pygame.draw.rect(s, (170, 230, 255, 120), s.get_rect(), border_radius=12)
    pygame.draw.lines(s, (255, 255, 255, 200), False, [(10, 20), (22, 30), (30, 18), (40, 36)], 2)
    pygame.draw.lines(s, (255, 255, 255, 160), False, [(18, 44), (28, 40), (36, 50)], 2)
    return s


CELL_ICE = 60
