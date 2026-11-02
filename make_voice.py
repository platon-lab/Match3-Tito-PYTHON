# -*- coding: utf-8 -*-
"""Запускать один раз на компьютере (нужен интернет и pip install gtts).

Скачивает всю озвучку в папку voice/. Потом папка voice/ лежит в проекте,
buildozer упаковывает её в APK, и игра озвучивает без интернета.

    pip install gtts
    python make_voice.py
"""
import os

from gtts import gTTS

from config import BUNDLED_VOICE_DIR, voice_name
from story import all_voice_texts


def main():
    os.makedirs(BUNDLED_VOICE_DIR, exist_ok=True)
    texts = all_voice_texts()
    made = 0
    for i, text in enumerate(texts, 1):
        path = os.path.join(BUNDLED_VOICE_DIR, voice_name(text))
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        print(f"[{i}/{len(texts)}] {text}")
        gTTS(text=text, lang="ru").save(path)
        made += 1
    print(f"Готово. Новых файлов: {made}, всего реплик: {len(texts)}. Папка: {BUNDLED_VOICE_DIR}")


if __name__ == "__main__":
    main()
