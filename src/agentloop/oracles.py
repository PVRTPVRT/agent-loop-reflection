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


def oracle_simulate_ttl_lru(capacity, events):
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise TypeError("capacity must be an integer")
    if capacity < 0:
        raise ValueError("capacity must be a non-negative integer")
    if not isinstance(events, list):
        raise TypeError("events must be a list")

    cache = {}
    outputs = []
    previous_time = None
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict):
            raise TypeError(f"event {index} must be an object")
        operation = event.get("op")
        timestamp = event.get("time")
        key = event.get("key")
        if isinstance(timestamp, bool) or not isinstance(timestamp, int):
            raise TypeError(f"event {index} time must be an integer")
        if previous_time is not None and timestamp < previous_time:
            raise ValueError("event times must be non-decreasing")
        if not isinstance(key, str):
            raise TypeError(f"event {index} key must be a string")
        previous_time = timestamp

        expired = [
            cached_key
            for cached_key, (_, expires_at) in cache.items()
            if timestamp >= expires_at
        ]
        for cached_key in expired:
            del cache[cached_key]

        if operation == "put":
            ttl = event.get("ttl")
            if isinstance(ttl, bool) or not isinstance(ttl, int) or ttl <= 0:
                raise ValueError(f"event {index} ttl must be a positive integer")
            if "value" not in event:
                raise ValueError(f"event {index} put requires value")
            cache.pop(key, None)
            if capacity == 0:
                continue
            cache[key] = (event["value"], timestamp + ttl)
            while len(cache) > capacity:
                del cache[next(iter(cache))]
        elif operation == "get":
            if key not in cache:
                outputs.append(None)
                continue
            value, expires_at = cache.pop(key)
            cache[key] = (value, expires_at)
            outputs.append(value)
        else:
            raise ValueError(f"event {index} op must be 'put' or 'get'")

    return outputs


ORACLES: dict[str, Callable[..., Any]] = {
    "add": oracle_add,
    "factorial": oracle_factorial,
    "fibonacci": oracle_fibonacci,
    "is_palindrome": oracle_is_palindrome,
    "clamp": oracle_clamp,
    "count_vowels": oracle_count_vowels,
    "deduplicate": oracle_deduplicate,
    "flatten_once": oracle_flatten_once,
    "simulate_ttl_lru": oracle_simulate_ttl_lru,
}
