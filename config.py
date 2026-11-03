# -*- coding: utf-8 -*-
"""Настройки игры, сохранение и генератор уровней."""
import hashlib
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
VOICE_DIR = os.path.join(DATA_DIR, "tito_voice")        # озвучка, скачанная во время игры
BUNDLED_VOICE_DIR = os.path.join(HERE, "voice")          # готовые mp3 (см. make_voice.py)
DEBUG_FILE = os.path.join(HERE, "DEBUG.txt")


def debug_enabled():
    """Читает DEBUG.txt. Если первое слово в файле ON, в главном меню тап по Тито открывает дебаг-меню.
    Любое другое содержимое (или отсутствие файла) означает, что дебаг выключен."""
    try:
        with open(DEBUG_FILE, "r", encoding="utf-8-sig") as f:
            words = f.read().split()
    except Exception:
        return False
    return bool(words) and words[0].upper() == "ON"


BASE_W, BASE_H = 540, 960
FPS = 60
ROWS = COLS = 8
CELL = 60
BX, BY = 30, 265
GEM_R = 23
MAX_LEVEL = 1000

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

# 6 видов монстров: слизь, летучая мышь, призрак, паук, циклоп, огонёк
MONSTER_COLORS = [
    (120, 200, 90),
    (150, 90, 215),
    (90, 150, 235),
    (150, 110, 80),
    (235, 130, 50),
    (235, 90, 160),
]
MONSTER_NAMES = ["Слизняк", "Летучая мышь", "Призрак", "Паук", "Циклоп", "Огонёк"]

DISTRICTS = ["Двор", "Улица", "Парк", "Пляж", "Кухня", "Подвал", "Крыши", "Ярмарка",
             "Замок", "Логово", "Болото", "Метро", "Чердак", "Космодром"]
HINTS = [
    "Совпадение рядом с монстром бьёт его по голове",
    "Антиматерия взрывает свою строку и столбец",
    "Бомба взрывает квадрат 3 на 3",
    "Магнит убирает все фишки одного цвета",
    "Молния бьёт по случайным клеткам",
    "Таймер-бомбу можно обезвредить совпадением рядом",
    "Паутину рвёт совпадение прямо в её клетке",
    "Цепи держат фишку, пока их не разорвёшь дважды",
    "Камень выдерживает три удара",
    "Слизь растёт, если её не трогать",
    "Кирпич выдерживает два удара, лёд — один",
    "Каскады дают больше очков",
    "Не торопись с последним монстром",
    "Туман скрывает поле, но место вокруг фишки видно",
    "Когда гравитация перевёрнута, фишки летят вверх",
]

# препятствия: сколько ударов нужно, чтобы убрать
OBST_HP = {"ice": 1, "web": 1, "brick": 2, "chain": 2, "stone": 3, "slime": 1}
MECH_NAMES = {
    "collect": "сбор", "ice": "лёд", "brick": "кирпичи", "web": "паутина", "chain": "цепи",
    "stone": "камни", "slime": "слизь", "monsters": "монстры", "timers": "таймер-бомбы",
    "gravity": "гравитация вверх", "fog": "туман", "shuffle": "перемешивание",
}

# боссы: каждые BOSS_EVERY уровней, всего 20 (до уровня 1000)
BOSS_EVERY = 50
BOSS_NAMES = [
    "Мурзик-гигант", "Слизень-король", "Летучая мышь-барон", "Призрак-граф", "Паук-королева",
    "Циклоп-колосс", "Мурзик-мститель", "Слизень-герцог", "Мышиный князь", "Тень-невидимка",
    "Пиявка-царица", "Голубь-громовержец", "Крысиный барон", "Саранча-ведьма", "Ледяной змей",
    "Огненный кот", "Чёрный ворон", "Механический Мурзик", "Королевский циклоп", "Мурзик-император",
]
BOSS_COLORS = [
    (200, 150, 255), (120, 200, 90), (150, 90, 215), (90, 150, 235), (150, 110, 80),
    (235, 130, 50), (210, 120, 230), (140, 220, 110), (170, 170, 180), (110, 110, 150),
    (60, 180, 150), (120, 170, 230), (160, 120, 90), (150, 200, 60), (130, 220, 240),
    (255, 110, 60), (80, 80, 110), (160, 170, 190), (230, 90, 70), (255, 200, 90),
]

BG_THEMES = {
    "street": ((90, 160, 235), (210, 235, 255)),
    "night": ((20, 15, 50), (70, 40, 110)),
    "arena": ((70, 20, 60), (12, 8, 26)),
    "forest": ((40, 110, 70), (12, 36, 24)),
    "cave": ((40, 34, 46), (10, 8, 14)),
    "lab": ((30, 70, 80), (8, 22, 30)),
    "fire": ((140, 50, 20), (30, 8, 10)),
    "ice": ((150, 210, 245), (40, 70, 120)),
}

# вступление (время в секундах, кто говорит, текст)
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

DEFAULT_SAVE = {
    "level": 1,
    "best": 0,
    "intro_done": False,
    "sound": True,
    "voice": True,
    "seen": [],          # какие механики уже показаны в катсценах
    "game": None,
}


def load_save():
    data = json.loads(json.dumps(DEFAULT_SAVE))
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


def voice_name(text):
    """Имя файла озвучки одной реплики (одинаково на ПК и на телефоне)."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12] + ".mp3"


def make_level(n):
    """Уровень n всегда одинаковый: случайность берётся из генератора с seed на основе n.

    Сложность растёт медленно: механики открываются постепенно, препятствий и монстров немного,
    а особых фишек выдаётся столько же, сколько раньше (spec_budget, не больше двух на поле)."""
    rng = random.Random(n * 7919 + 17)
    boss = n % BOSS_EVERY == 0
    hard = n % 20 == 0 and not boss
    mult = 1.2 if hard else 1.0
    colors = min(6, 4 + (n - 1) // 25)
    top = (rng.randrange(20, 110), rng.randrange(20, 110), rng.randrange(30, 120))
    cfg = {
        "n": n,
        "boss": boss,
        "hard": hard,
        "colors": colors,
        "name": f"{DISTRICTS[(n - 1) % len(DISTRICTS)]} {n}",
        "top": top,
        "bottom": tuple(c // 3 for c in top),
        "score": int((220 + 60 * math.sqrt(n)) * mult),
        "collect": {},
        "obst": {},
        "monsters": 0,
        "timers": 0,
        "timer_len": 0,
        "gravity": False,
        "fog": False,
        "shuffle_every": 0,
        "slime_every": 3,
        "spec_budget": 2 if n < 10 else (3 if n < 30 else 4),
        "hint": rng.choice(HINTS),
        "moves": None,
        "time": None,
        "mech": [],
    }

    if n >= 2 and rng.random() < 0.6:
        k = rng.randrange(colors)
        cfg["collect"][k] = min(30, int((5 + n // 4) * mult))
        if n >= 30 and rng.random() < 0.3:
            k2 = (k + 1 + rng.randrange(colors - 1)) % colors
            cfg["collect"][k2] = min(25, int((4 + n // 5) * mult))

    obst = cfg["obst"]
    if n >= 3 and rng.random() < 0.45:
        obst["ice"] = min(8, int((2 + n // 8) * mult))
    if n >= 8 and rng.random() < 0.3:
        obst["web"] = min(6, 2 + n // 15)
    if n >= 8 and rng.random() < 0.4:
        obst["brick"] = min(8, 2 + n // 10)
    if n >= 20 and rng.random() < 0.2:
        obst["chain"] = min(5, 2 + n // 25)
    if n >= 30 and rng.random() < 0.2:
        obst["stone"] = min(4, 2 + n // 30)
    if n >= 25 and rng.random() < 0.2:
        obst["slime"] = 1 + min(1, n // 80)
    while sum(obst.values()) > 14:
        big = max(obst, key=obst.get)
        obst[big] -= 1
        if obst[big] <= 0:
            del obst[big]

    if n > 10:
        cfg["monsters"] = min(5, 1 + (n - 11) // 12)
    if n >= 25 and rng.random() < 0.15:
        cfg["timers"] = 1 if n < 60 else 2
        cfg["timer_len"] = max(6, 10 - n // 40)
    if n >= 40 and rng.random() < 0.12:
        cfg["gravity"] = True
    if n >= 50 and rng.random() < 0.1:
        cfg["fog"] = True
    if n >= 60 and rng.random() < 0.1:
        cfg["shuffle_every"] = max(6, 12 - n // 60)

    if n >= 4 and rng.random() < 0.2:
        cfg["time"] = max(60, int((100 - n // 5) * (0.85 if hard else 1.0)))
    else:
        cfg["moves"] = max(18, 32 - n // 10) - (3 if hard else 0)

    mech = []
    if cfg["collect"]:
        mech.append("collect")
    mech += [k for k in ("ice", "web", "brick", "chain", "stone", "slime") if k in obst]
    if cfg["monsters"]:
        mech.append("monsters")
    if cfg["timers"]:
        mech.append("timers")
    if cfg["gravity"]:
        mech.append("gravity")
    if cfg["fog"]:
        mech.append("fog")
    if cfg["shuffle_every"]:
        mech.append("shuffle")
    cfg["mech"] = mech
    return cfg


def goal_text(cfg):
    parts = []
    if cfg.get("score"):
        parts.append(f"набрать {cfg['score']} очков")
    for k, c in cfg.get("collect", {}).items():
        parts.append(f"собрать {c} {SHAPE_GEN[k]}")
    total = sum(cfg.get("obst", {}).values())
    if total:
        parts.append(f"разбить препятствия ({total})")
    if cfg.get("monsters"):
        parts.append(f"победить монстров ({cfg['monsters']})")
    limit = f"за {cfg['moves']} ходов" if cfg.get("moves") else f"за {cfg['time']} сек"
    return "Цель: " + ", ".join(parts) + " " + limit
