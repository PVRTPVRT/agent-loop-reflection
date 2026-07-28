from collections import OrderedDict
from typing import Any


def simulate_ttl_lru(capacity: int, events: list[dict[str, Any]]) -> list[Any]:
    """Recorded R1 failure: incorrectly assumes LRU order is expiry order."""
    if capacity < 0:
        raise ValueError("capacity must be non-negative")

    cache: OrderedDict[str, tuple[Any, int]] = OrderedDict()
    results: list[Any] = []

    def evict_expired(current_time: int) -> None:
        while cache:
            key = next(iter(cache))
            _, expires_at = cache[key]
            if expires_at <= current_time:
                cache.popitem(last=False)
            else:
                break

    for event in events:
        current_time = event["time"]
        evict_expired(current_time)
        key = event["key"]

        if event["op"] == "put":
            if capacity == 0:
                continue
            cache.pop(key, None)
            cache[key] = (event["value"], current_time + event["ttl"])
            while len(cache) > capacity:
                cache.popitem(last=False)
        elif event["op"] == "get":
            if key not in cache:
                results.append(None)
                continue
            value, _ = cache[key]
            cache.move_to_end(key)
            results.append(value)
        else:
            raise ValueError(f"unknown op: {event['op']}")

    return results
