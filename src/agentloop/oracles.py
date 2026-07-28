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


def oracle_decode_frames_by_chunk(chunks, max_frame_size):
    if isinstance(max_frame_size, bool) or not isinstance(max_frame_size, int):
        raise TypeError("max_frame_size must be an integer")
    if max_frame_size < 0:
        raise ValueError("max_frame_size must be non-negative")
    if not isinstance(chunks, list):
        raise TypeError("chunks must be a list")

    buffer = bytearray()
    expected_length = None
    outputs = []
    for index, chunk in enumerate(chunks, 1):
        if not isinstance(chunk, str):
            raise TypeError(f"chunk {index} must be a string")
        if len(chunk) % 2 or any(
            character not in "0123456789abcdefABCDEF"
            for character in chunk
        ):
            raise ValueError(
                f"chunk {index} must be an even-length hexadecimal string"
            )
        buffer.extend(bytes.fromhex(chunk))
        completed = []
        while True:
            if expected_length is None:
                if len(buffer) < 4:
                    break
                expected_length = int.from_bytes(buffer[:4], "big")
                del buffer[:4]
                if expected_length > max_frame_size:
                    raise ValueError(
                        f"frame length {expected_length} exceeds max_frame_size"
                    )
            if len(buffer) < expected_length:
                break
            payload = bytes(buffer[:expected_length])
            del buffer[:expected_length]
            completed.append(payload.hex())
            expected_length = None
        outputs.append(completed)

    if expected_length is not None or buffer:
        raise ValueError("incomplete frame at end of input")
    return outputs


def oracle_process_idempotent_transfers(initial_balances, events):
    if not isinstance(initial_balances, dict):
        raise TypeError("initial_balances must be a dictionary")
    balances = {}
    for account, balance in initial_balances.items():
        if (
            not isinstance(account, str)
            or not account
            or isinstance(balance, bool)
            or not isinstance(balance, int)
            or balance < 0
        ):
            raise ValueError(
                "initial balances must map account names to non-negative integers"
            )
        balances[account] = balance
    if not isinstance(events, list):
        raise TypeError("events must be a list")

    seen = {}
    results = []
    required_fields = {"id", "from", "to", "amount"}
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict) or set(event) != required_fields:
            raise ValueError(
                f"event {index} must contain exactly id, from, to, and amount"
            )
        event_id = event["id"]
        source = event["from"]
        destination = event["to"]
        amount = event["amount"]
        if (
            not isinstance(event_id, str)
            or not event_id
            or not isinstance(source, str)
            or not source
            or not isinstance(destination, str)
            or not destination
            or source == destination
            or isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount <= 0
        ):
            raise ValueError(f"event {index} is invalid")

        signature = (source, destination, amount)
        if event_id in seen:
            original_signature, cached_result = seen[event_id]
            if signature != original_signature:
                raise ValueError(
                    f"event {index} reuses id {event_id!r} with a different payload"
                )
            results.append(dict(cached_result))
            continue

        source_balance = balances.get(source, 0)
        destination_balance = balances.get(destination, 0)
        if source_balance < amount:
            status = "rejected"
        else:
            status = "applied"
            source_balance -= amount
            destination_balance += amount
            balances[source] = source_balance
            balances[destination] = destination_balance
        result = {
            "id": event_id,
            "status": status,
            "from_balance": source_balance,
            "to_balance": destination_balance,
        }
        seen[event_id] = (signature, result)
        results.append(dict(result))

    return {"results": results, "balances": balances}


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
    "decode_frames_by_chunk": oracle_decode_frames_by_chunk,
    "process_idempotent_transfers": oracle_process_idempotent_transfers,
}
