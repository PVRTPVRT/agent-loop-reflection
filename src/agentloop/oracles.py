"""Trusted local reference functions used to validate generated test outcomes."""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from typing import Any


def oracle_add(a, b):
    return a + b


def oracle_factorial(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    return math.factorial(n)


def oracle_fibonacci(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def oracle_is_palindrome(text):
    normalized = re.sub(r"[^A-Za-z0-9]", "", text).lower()
    return normalized == normalized[::-1]


def oracle_clamp(value, lower, upper):
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    return min(max(value, lower), upper)


def oracle_count_vowels(text):
    return sum(character.lower() in "aeiou" for character in text)


def oracle_deduplicate(items):
    return list(dict.fromkeys(items))


def oracle_flatten_once(items):
    result = []
    for item in items:
        result.extend(item if isinstance(item, list) else [item])
    return result


ORACLES: dict[str, Callable[..., Any]] = {
    "add": oracle_add,
    "factorial": oracle_factorial,
    "fibonacci": oracle_fibonacci,
    "is_palindrome": oracle_is_palindrome,
    "clamp": oracle_clamp,
    "count_vowels": oracle_count_vowels,
    "deduplicate": oracle_deduplicate,
    "flatten_once": oracle_flatten_once,
}
