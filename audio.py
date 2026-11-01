# -*- coding: utf-8 -*-
"""Звуки и озвучка. Озвучка скачивается один раз через gTTS (нужен интернет)."""
import hashlib
import math
import os
import time
from array import array

import pygame

from config import VOICE_DIR


def voice_path(text):
    h = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    return os.path.join(VOICE_DIR, h + ".mp3")


def voice_worker(texts, status):
    """Фоновая загрузка озвучки. status — словарь, который читает меню настроек."""
    try:
        from gtts import gTTS
    except Exception:
        status["state"] = "nogtts"
        return
    try:
        os.makedirs(VOICE_DIR, exist_ok=True)
    except Exception:
        status["state"] = "nodir"
        return
    status["state"] = "loading"
    fails = 0
    for text in texts:
        path = voice_path(text)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            status["done"] += 1
            continue
        try:
            tmp = path + ".tmp"
            gTTS(text=text, lang="ru").save(tmp)
            os.replace(tmp, path)
            status["done"] += 1
            fails = 0
        except Exception:
            fails += 1
            if fails >= 3:
                status["state"] = "offline"
                return
            time.sleep(1.0)
    status["state"] = "done"


def _tone(freq, dur, vol=0.25, sweep=0.0, decay=2.5):
    """Синусоидальный звук (стерео 16 бит). sweep — изменение частоты."""
    n = max(1, int(44100 * dur))
    out = array("h")
    for i in range(n):
        t = i / 44100.0
        phase = 2 * math.pi * (freq * t + sweep * t * t / (2 * dur))
        env = (1 - i / n) ** decay
        v = int(32767 * vol * env * math.sin(phase))
        out.append(v)
        out.append(v)
    return out


class Audio:
    def __init__(self, save):
        self.save = save
        self.ok = False
        self.sfx = {}
        self.voice_ch = None
        self.voice_cache = {}
        try:
            if pygame.mixer.get_init():
                defs = {
                    "swap": _tone(520, 0.07, 0.18),
                    "bad": _tone(180, 0.15, 0.2, sweep=-60),
                    "pop": _tone(700, 0.12, 0.22, sweep=900),
                    "cascade": _tone(1000, 0.12, 0.2, sweep=600),
                    "fall": _tone(260, 0.08, 0.10),
                    "click": _tone(900, 0.05, 0.15),
                    "bomb": _tone(420, 0.35, 0.3, sweep=-340, decay=1.5),
                    "shot": _tone(950, 0.05, 0.12, sweep=-400),
                    "hit": _tone(300, 0.12, 0.25, sweep=-200),
                    "boom": _tone(160, 0.25, 0.3, sweep=-80, decay=1.8),
                    "win": (_tone(523, 0.12, 0.25, decay=0.5) + _tone(659, 0.12, 0.25, decay=0.5)
                            + _tone(784, 0.12, 0.25, decay=0.5) + _tone(1046, 0.35, 0.25, decay=0.8)),
                    "lose": (_tone(392, 0.2, 0.22, decay=1.2) + _tone(330, 0.2, 0.22, decay=1.2)
                             + _tone(262, 0.45, 0.22, decay=1.5)),
                }
                for name, arr in defs.items():
                    self.sfx[name] = pygame.mixer.Sound(buffer=arr.tobytes())
                self.ok = True
        except Exception:
            self.ok = False

    def play(self, name):
        if self.ok and self.save.get("sound", True) and name in self.sfx:
            try:
                self.sfx[name].play()
            except Exception:
                pass

    def play_voice(self, text):
        self.stop_voice()
        if not self.ok or not self.save.get("voice", True):
            return
        path = voice_path(text)
        if not os.path.exists(path):
            return
        try:
            snd = self.voice_cache.get(path)
            if snd is None:
                snd = pygame.mixer.Sound(path)
                self.voice_cache[path] = snd
            self.voice_ch = snd.play()
        except Exception:
            self.voice_ch = None

    def stop_voice(self):
        if self.voice_ch is not None:
            try:
                self.voice_ch.stop()
            except Exception:
                pass
        self.voice_ch = None
