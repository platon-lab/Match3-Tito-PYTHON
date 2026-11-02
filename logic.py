# -*- coding: utf-8 -*-
"""Логика поля: совпадения, падение фишек, особые фишки и таймер-бомбы."""
import random

from config import ROWS, COLS


class Star:
    """Антиматерия (из 4 в ряд): по тапу взрывает строку и столбец."""


class Bomb:
    """Бомба (из 5 в ряд): по тапу взрывает квадрат 3 на 3."""


class Magnet:
    """Магнит (из 5 в ряд, вместо бомбы): по тапу убирает все фишки одного цвета."""


class Lightning:
    """Молния (из 4 в ряд, вместо антиматерии): по тапу бьёт по 6 случайным клеткам."""


class Timer:
    """Таймер-бомба: каждый удачный ход уменьшает left. При нуле взрывает 3 на 3,
    если рядом не было совпадения, которое её обезвредило."""

    def __init__(self, left=6):
        self.left = left


class Monster:
    """Монстр с 3 HP. Теряет 1 HP, когда рядом совпадает три в ряд."""

    def __init__(self, species=0, hp=3):
        self.species = species
        self.hp = hp
        self.flash = 0.0


SPECIALS = (Star, Bomb, Magnet, Lightning)


def is_gem(v):
    return type(v) is int


def is_special(v):
    return isinstance(v, SPECIALS)


def swap_cells(board, a, b):
    (r1, c1), (r2, c2) = a, b
    board[r1][c1], board[r2][c2] = board[r2][c2], board[r1][c1]


def find_matches(board):
    matched = set()
    for r in range(ROWS):
        for c in range(COLS - 2):
            v = board[r][c]
            if is_gem(v) and v == board[r][c + 1] == board[r][c + 2]:
                matched.update({(r, c), (r, c + 1), (r, c + 2)})
    for c in range(COLS):
        for r in range(ROWS - 2):
            v = board[r][c]
            if is_gem(v) and v == board[r + 1][c] == board[r + 2][c]:
                matched.update({(r, c), (r + 1, c), (r + 2, c)})
    return matched


def has_possible_move(board, blocked=frozenset()):
    """Есть ли ход. Особая фишка на поле — тоже ход (её можно активировать)."""
    for row in board:
        for v in row:
            if is_special(v):
                return True
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in ((0, 1), (1, 0)):
                r2, c2 = r + dr, c + dc
                if r2 >= ROWS or c2 >= COLS:
                    continue
                if (r, c) in blocked or (r2, c2) in blocked:
                    continue
                swap_cells(board, (r, c), (r2, c2))
                ok = bool(find_matches(board))
                swap_cells(board, (r, c), (r2, c2))
                if ok:
                    return True
    return False


def make_board(n_colors):
    """Поле без готовых рядов и с хотя бы одним возможным ходом."""
    while True:
        board = [[None] * COLS for _ in range(ROWS)]
        for r in range(ROWS):
            for c in range(COLS):
                options = list(range(n_colors))
                random.shuffle(options)
                for v in options:
                    if c >= 2 and board[r][c - 1] == v and board[r][c - 2] == v:
                        continue
                    if r >= 2 and board[r - 1][c] == v and board[r - 2][c] == v:
                        continue
                    board[r][c] = v
                    break
        if has_possible_move(board):
            return board


def gravity_fill(board, n_colors, up=False):
    """Падение объектов и появление новых фишек. up=True — гравитация перевёрнута.
    Возвращает список (объект, откуда_строка, куда_строка, колонка) для анимации."""
    moves = []
    for c in range(COLS):
        vals = [(board[r][c], r) for r in range(ROWS) if board[r][c] is not None]
        n_new = ROWS - len(vals)
        if up:
            for k, (v, src) in enumerate(vals):
                board[k][c] = v
                moves.append((v, src, k, c))
            for i in range(n_new):
                dst = len(vals) + i
                v = random.randrange(n_colors)
                board[dst][c] = v
                moves.append((v, dst + n_new, dst, c))
        else:
            for k, (v, src) in enumerate(vals):
                dst = n_new + k
                board[dst][c] = v
                moves.append((v, src, dst, c))
            for i in range(n_new):
                v = random.randrange(n_colors)
                board[i][c] = v
                moves.append((v, i - n_new, i, c))
    return moves


def reshuffle_gems(board, n_colors, blocked=frozenset()):
    """Если ходов не осталось: перемешивает только обычные фишки вне заблокированных клеток."""
    cells = [(r, c) for r in range(ROWS) for c in range(COLS)
             if is_gem(board[r][c]) and (r, c) not in blocked]
    vals = [board[r][c] for r, c in cells]
    for _ in range(300):
        random.shuffle(vals)
        for (r, c), v in zip(cells, vals):
            board[r][c] = v
        if not find_matches(board) and has_possible_move(board, blocked):
            return
    for r, c in cells:
        board[r][c] = random.randrange(n_colors)
