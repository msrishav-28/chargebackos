from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")


def mulberry32(seed: int) -> Callable[[], float]:
    a = seed & 0xFFFFFFFF

    def next_float() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = (a ^ (a >> 15)) * (1 | a)
        t &= 0xFFFFFFFF
        t = ((t + ((t ^ (t >> 7)) * (61 | t))) ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return next_float


def rand_int(rng: Callable[[], float], lo: int, hi: int) -> int:
    return lo + math.floor(rng() * (hi - lo + 1))


def pick(rng: Callable[[], float], items: Sequence[T]) -> T:
    return items[math.floor(rng() * len(items))]


def chance(rng: Callable[[], float], p: float) -> bool:
    return rng() < p


def randn(rng: Callable[[], float]) -> float:
    u = max(1e-9, rng())
    v = rng()
    return math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * v)


def clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


def shuffle(rng: Callable[[], float], arr: list[T]) -> list[T]:
    a = list(arr)
    for i in range(len(a) - 1, 0, -1):
        j = math.floor(rng() * (i + 1))
        a[i], a[j] = a[j], a[i]
    return a


def hash8(s: str) -> str:
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return f"{h:08x}"[:8]


def fnv_hash(parts: list[str]) -> str:
    h = 2166136261
    s = "|".join(parts)
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return f"{h:08x}"
