# -*- coding: utf-8 -*-
"""Сюжет: катсцены, новые механики, главы, боссы и список всех реплик для озвучки.

Реплика (beat) — кадр катсцены. Поля: speaker (NAR / TITO / MUR / BOSS), text,
необязательные: bg (фон), prop (реквизит), cast (кто на сцене), title (заголовок),
boss (номер босса), shake (тряска), sound (звук), name и color (для BOSS)."""
from config import HINTS, BOSS_NAMES, BOSS_COLORS, BOSS_EVERY, INTRO_LINES


def B(speaker, text, **kw):
    d = {"speaker": speaker, "text": text}
    d.update(kw)
    return d


RESULT_WON = "Тито гордится тобой! Гав!"
RESULT_LOST = "Не получилось. Тито не сдаётся!"
RESULT_BOSS_WON = "Босс повержен! Гав-гав!"
RESULT_LINES = [RESULT_WON, RESULT_LOST, RESULT_BOSS_WON]

# катсцена при первом появлении каждой механики
MECH_BEATS = {
    "collect": [
        B("NAR", "Фишки-самоцветы рассыпались по полю. Нужные надо собрать до конца.",
          bg="street", prop="gem", cast=["TITO"], title="НОВОЕ: СБОР"),
        B("TITO", "Самоцветы такие красивые! Соберу все до единого. Гав!",
          bg="street", prop="gem", cast=["TITO"]),
    ],
    "ice": [
        B("NAR", "На поле появился лёд. Он тает от одного совпадения рядом.",
          bg="ice", prop="ice", cast=["TITO"], title="НОВОЕ: ЛЁД"),
        B("TITO", "Растоплю всё! У меня горячий нос. Гав!", bg="ice", prop="ice", cast=["TITO"]),
    ],
    "brick": [
        B("NAR", "Кирпичная кладка выдерживает два удара. Не торопись.",
          bg="street", prop="brick", cast=["TITO"], title="НОВОЕ: КИРПИЧ"),
        B("MUR", "Два удара? Да ты за год не справишься, пёсик!", bg="street", prop="brick", cast=["MUR"]),
    ],
    "web": [
        B("NAR", "Паутина держит фишку. Пока её не порвёшь, фишка не сдвинется.",
          bg="forest", prop="web", cast=["TITO"], title="НОВОЕ: ПАУТИНА"),
        B("TITO", "Фу, липко! Ладно, порву её совпадением прямо в клетке!",
          bg="forest", prop="web", cast=["TITO"]),
    ],
    "chain": [
        B("NAR", "Цепи заперли фишку. Их нужно разорвать дважды.",
          bg="cave", prop="chain", cast=["TITO"], title="НОВОЕ: ЦЕПИ"),
        B("MUR", "Не порвёшь! Эти цепи сковал сам Мурзик!", bg="cave", prop="chain", cast=["MUR"]),
    ],
    "stone": [
        B("NAR", "Каменная глыба стоит на пути. Чтобы её расколоть, нужно три удара.",
          bg="cave", prop="stone", cast=["TITO"], title="НОВОЕ: КАМНИ"),
        B("TITO", "Камень? Подумаешь. Я и не таких грыз!", bg="cave", prop="stone", cast=["TITO"]),
    ],
    "slime": [
        B("NAR", "Слизь растёт, если её не трогать. Очищай её, пока не поздно.",
          bg="forest", prop="slime", cast=["TITO"], title="НОВОЕ: СЛИЗЬ"),
        B("TITO", "Фу, какая гадость! Скорее всё очистить!", bg="forest", prop="slime", cast=["TITO"]),
    ],
    "monsters": [
        B("NAR", "Из-под кровати вылезли монстры. Бей их совпадениями рядом.",
          bg="night", prop="monster", cast=["TITO"], title="НОВОЕ: МОНСТРЫ"),
        B("TITO", "Гав! Сейчас я их всех разгоню!", bg="night", prop="monster", cast=["TITO"]),
    ],
    "timers": [
        B("NAR", "Таймер-бомба тикает! Обезвреди её совпадением рядом, пока не взорвалась.",
          bg="night", prop="timer", cast=["TITO"], title="НОВОЕ: ТАЙМЕРЫ"),
        B("TITO", "Быстро! Ставлю совпадение рядом!", bg="night", prop="timer", cast=["TITO"]),
    ],
    "gravity": [
        B("NAR", "Гравитация перевернулась: фишки теперь летят вверх.",
          bg="lab", prop="gravity", cast=["TITO"], title="НОВОЕ: ГРАВИТАЦИЯ"),
        B("MUR", "Ха! Пусть всё летает, как хочет! Тито не удержит равновесие.",
          bg="lab", prop="gravity", cast=["MUR"]),
    ],
    "fog": [
        B("NAR", "Туман закрыл поле. Видно только то, что рядом с выбранной фишкой.",
          bg="night", prop="fog", cast=["TITO"], title="НОВОЕ: ТУМАН"),
        B("TITO", "Ничего не вижу... Ладно, пойду по запаху!", bg="night", prop="fog", cast=["TITO"]),
    ],
    "shuffle": [
        B("NAR", "Поле иногда перемешивается само. Держи глаза открытыми.",
          bg="lab", prop="shuffle", cast=["TITO"], title="НОВОЕ: ПЕРЕМЕШИВАНИЕ"),
        B("MUR", "Пусть каждый ход будет сюрпризом!", bg="lab", prop="shuffle", cast=["MUR"]),
    ],
}

# перед каждым тяжёлым уровнем (n кратно 20)
HARD_BEATS = [
    B("NAR", "Этот уровень тяжелее остальных. Тито чувствует опасность.", bg="night",
      title="ТЯЖЁЛЫЙ УРОВЕНЬ"),
    B("MUR", "Не выйдет у тебя, пёсик!", bg="night", cast=["MUR"]),
    B("TITO", "Посмотрим! Гав!", bg="night", cast=["TITO"], shake=True),
]

# сюжетные главы: каждые 10 уровней, по кругу
CHAPTERS = [
    [B("NAR", "Тито прошёл уже десять районов Косточкино.", bg="street", title="ГЛАВА 1"),
     B("TITO", "Осталось найти Золотую косточку. Чувствую, она где-то у Мурзика!", bg="street", cast=["TITO"])],
    [B("NAR", "Следы самоцветов ведут в парк, где гуляют голуби.", bg="forest", title="ГЛАВА 2"),
     B("TITO", "Голуби, не видели мою косточку? Нет? Ну ладно. Гав!", bg="forest", cast=["TITO"])],
    [B("NAR", "В подвале пахнет сыром и чем-то очень подозрительным.", bg="cave", title="ГЛАВА 3"),
     B("MUR", "Кто это лезет в мой подвал? Ах, это ты, пёсик!", bg="cave", cast=["MUR"])],
    [B("NAR", "На крыше сильный ветер. Самоцветы кружатся в воздухе.", bg="night", title="ГЛАВА 4"),
     B("TITO", "Не улетайте! Сейчас я вас поймаю! Гав!", bg="night", cast=["TITO"])],
    [B("NAR", "Замок Мурзика охраняют тени. Тито собирает последние силы.", bg="fire", title="ГЛАВА 5"),
     B("TITO", "Я почти у цели. Косточка совсем рядом!", bg="fire", cast=["TITO"])],
    [B("NAR", "Ярмарка сияет огнями. Кто-то ждёт Тито в центре.", bg="ice", title="ГЛАВА 6"),
     B("MUR", "Ну здравствуй, Тито. Тебе не понравится то, что будет дальше.", bg="ice", cast=["MUR"])],
]

# (что говорит босс, что отвечает Тито) — порядок как в BOSS_NAMES
BOSS_TALK = [
    ("Тито! Косточка теперь моя! Мур-р-р!", "Верни косточку, Мурзик! Гав!"),
    ("Я король слизи! Ты тут ничего не очистишь!", "Очищу всё, до последней капли!"),
    ("Я лечу над полем и вижу всё сверху!", "Тогда я прыгну выше! Гав!"),
    ("Я призрак, меня не поймать!", "Посмотрим, кто из нас страшнее!"),
    ("Мои нити опутают тебя, Тито!", "Порву все нитки, даже самую тонкую!"),
    ("Один глаз, но он видит всё!", "Тогда я буду двигаться быстрее твоего взгляда!"),
]


def boss_beats(n):
    """Катсцена перед боссом на уровне n (кратном BOSS_EVERY)."""
    b = max(1, n // BOSS_EVERY)
    k = (b - 1) % len(BOSS_NAMES)
    name, color = BOSS_NAMES[k], BOSS_COLORS[k]
    talk, reply = BOSS_TALK[k]
    return [
        B("NAR", f"Появляется босс: {name}", bg="arena", title=f"БОСС {b}", boss=k,
          cast=["TITO"], shake=True, sound="roar"),
        B("BOSS", talk, bg="arena", boss=k, cast=["TITO", "BOSS"], name=name, color=color, shake=True),
        B("TITO", reply, bg="arena", boss=k, cast=["TITO", "BOSS"]),
    ]


def new_mechanics(cfg, seen):
    """Механики уровня, которые игрок ещё не видел в катсцене."""
    return [m for m in cfg["mech"] if m not in seen]


def level_beats(cfg, new):
    """Катсцена перед уровнем: новые механики, глава каждые 10 уровней, тяжёлый уровень."""
    beats = []
    for m in new:
        beats += MECH_BEATS[m]
    n = cfg["n"]
    if n % 10 == 0 and not cfg["boss"]:
        beats += CHAPTERS[(n // 10 - 1) % len(CHAPTERS)]
    if cfg["hard"]:
        beats += HARD_BEATS
    return beats


def all_voice_texts():
    """Все реплики игры, которые нужно озвучить (для make_voice.py и фоновой загрузки)."""
    out = []

    def add(t):
        if t and t not in out:
            out.append(t)

    for beats in MECH_BEATS.values():
        for b in beats:
            add(b["text"])
    for b in HARD_BEATS:
        add(b["text"])
    for ch in CHAPTERS:
        for b in ch:
            add(b["text"])
    for k in range(len(BOSS_NAMES)):
        for b in boss_beats(BOSS_EVERY * (k + 1)):
            add(b["text"])
    for h in HINTS:
        add(h)
    for t in RESULT_LINES:
        add(t)
    for _, _, t in INTRO_LINES:
        add(t)
    return out
