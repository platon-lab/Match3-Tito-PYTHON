# -*- coding: utf-8 -*-
"""Настройки игры, сохранение и генератор бесконечных уровней."""
import json
import math
import os
import random
import sys

IS_ANDROID = hasattr(sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in os.environ
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("ANDROID_PRIVATE") or HERE
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    DATA_DIR = HERE
SAVE_FILE = os.path.join(DATA_DIR, "tito_save.json")
PHOTO_FILE = os.path.join(HERE, "tito.jpg")
VOICE_DIR = os.path.join(DATA_DIR, "tito_voice")

BASE_W, BASE_H = 540, 960
FPS = 60
ROWS = COLS = 8
CELL = 60
BX, BY = 30, 265
GEM_R = 23

# цвет и форма обычных фишек
GEMS = [
    ((235, 75, 85), "circle"),
    ((90, 205, 95), "square"),
    ((75, 135, 240), "triangle"),
    ((250, 210, 65), "diamond"),
    ((175, 95, 240), "star"),
    ((255, 145, 55), "hex"),
]
SHAPE_NAMES = ["Кружки", "Квадраты", "Треугольники", "Ромбы", "Звёзды", "Шестиугольники"]
SHAPE_GEN = ["кружочков", "квадратов", "треугольников", "ромбов", "звёзд", "шестиугольников"]
MONSTER_COLORS = [(120, 200, 90), (170, 95, 230), (235, 115, 60), (70, 175, 225)]
DISTRICTS = ["Двор", "Улица", "Парк", "Пляж", "Кухня", "Подвал", "Крыши", "Ярмарка", "Замок", "Логово"]
HINTS = [
    "Совпадение рядом с монстром бьёт его по голове",
    "Звезда антиматерии взрывает свою строку и столбец",
    "Каскады дают больше очков",
    "Лёд разбивается, когда совпадение проходит по нему",
    "Не торопись с последним монстром",
]

# вступление: (время в секундах, кто говорит, текст)
INTRO_LINES = [
    (0.3, "NAR", "Солнечным утром пёс Тито отправился гулять по городу Косточкино."),
    (3.4, "NAR", "В его рюкзаке лежали самые ценные вещи: Золотая косточка и волшебные самоцветы."),
    (7.1, "TITO", "Ой! Ремешок порвался!"),
    (8.6, "TITO", "Мои самоцветы! Где моя косточка?!"),
    (10.4, "NAR", "Тито оглянулся. За ним по дороге тянулся след из самоцветов."),
    (13.4, "TITO", "Ничего, я всё соберу до последнего! Гав!"),
    (17.2, "NAR", "А из кустов за ним уже следили чьи-то жёлтые глаза..."),
]
INTRO_LENGTH = 19.8
INTRO_TEXTS = [t for _, _, t in INTRO_LINES]

DEFAULT_SAVE = {
    "level": 1,
    "best": 0,
    "intro_done": False,
    "sound": True,
    "voice": True,
    "inf_moves": False,
    "start_stars": 0,
}


def load_save():
    data = dict(DEFAULT_SAVE)
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data.update(json.load(f))
    except Exception:
        pass
    data["level"] = max(1, int(data.get("level", 1)))
    return data


def write_save(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def make_level(n):
    """Уровень n всегда получается одинаковым (генератор на основе n)."""
    rng = random.Random(n * 7919 + 17)
    boss = n % 100 == 0
    hard = n % 20 == 0 and not boss
    mult = 1.5 if hard else 1.0
    colors = min(6, 4 + (n - 1) // 15)
    top = (rng.randrange(20, 110), rng.randrange(20, 110), rng.randrange(30, 120))
    cfg = {
        "n": n,
        "boss": boss,
        "hard": hard,
        "colors": colors,
        "name": f"{DISTRICTS[(n - 1) % len(DISTRICTS)]} {n}",
        "top": top,
        "bottom": tuple(c // 3 for c in top),
        "score": int((260 + 70 * math.sqrt(n)) * mult),
        "collect": {},
        "ice": 0,
        "monsters": 0,
        "hint": rng.choice(HINTS),
    }
    if n >= 2 and rng.random() < 0.6:
        k = rng.randrange(colors)
        cfg["collect"][k] = min(45, int((6 + n // 3) * mult))
        if n >= 30 and rng.random() < 0.4:
            k2 = (k + 1 + rng.randrange(colors - 1)) % colors
            cfg["collect"][k2] = min(45, int((5 + n // 4) * mult))
    if n >= 3 and rng.random() < 0.5:
        cfg["ice"] = min(30, int((3 + n // 5) * mult))
    if n > 10:
        cfg["monsters"] = min(12, 1 + (n - 11) // 6 + (1 if hard else 0))
    if n >= 4 and rng.random() < 0.25:
        cfg["time"] = max(35, int((80 - n // 4) * (0.8 if hard else 1.0)))
    else:
        cfg["moves"] = max(12, 28 - n // 8) - (5 if hard else 0)
    return cfg


def goal_text(cfg):
    parts = []
    if cfg.get("score"):
        parts.append(f"набрать {cfg['score']} очков")
    for k, c in cfg.get("collect", {}).items():
        parts.append(f"собрать {c} {SHAPE_GEN[k]}")
    if cfg.get("ice"):
        parts.append(f"разбить лёд ({cfg['ice']})")
    if cfg.get("monsters"):
        parts.append(f"победить монстров ({cfg['monsters']})")
    if cfg.get("moves"):
        limit = f"за {cfg['moves']} ходов"
    else:
        limit = f"за {cfg['time']} сек"
    return "Цель: " + ", ".join(parts) + " " + limit
