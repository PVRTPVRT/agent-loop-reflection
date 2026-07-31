from collections import OrderedDict
from typing import Any, Dict, List, Optional


def simulate_ttl_lru(capacity: int, events: List[Dict[str, Any]]) -> List[Optional[Any]]:
    """
    Simulate a TTL-based LRU cache.

    Rules:
    - capacity: non-negative integer; negative raises ValueError
    - events: sorted by non-decreasing integer time
    - Before each event, delete entries with time >= expires_at
    - put(key, value, ttl): insert/overwrite, expires_at = time + ttl, mark MRU, LRU-evict to capacity
    - get(key): if not hit return None, else return value and mark MRU
    - capacity == 0 stores nothing
    """
    if capacity < 0:
        raise ValueError("capacity must be non-negative")

    # OrderedDict maintains LRU order: oldest -> newest (MRU at end)
    # value stored as (value, expires_at)
    cache: "OrderedDict[str, tuple[Any, int]]" = OrderedDict()

    results: List[Optional[Any]] = []

    def purge(current_time: int) -> None:
        # Remove all entries with expires_at <= current_time
        while cache:
            k = next(iter(cache))
            _, expires_at = cache[k]
            if current_time >= expires_at:
                cache.popitem(last=False)
            else:
                break

    for ev in events:
        op = ev.get("op")
        t = ev.get("time")
        purge(t)

        if op == "put":
            if capacity == 0:
                continue
            key = ev["key"]
            value = ev["value"]
            ttl = ev["ttl"]
            expires_at = t + ttl

            if key in cache:
                cache.pop(key, None)
            cache[key] = (value, expires_at)  # insert as MRU

            # Evict LRU until within capacity
            while len(cache) > capacity:
                cache.popitem(last=False)

        elif op == "get":
            key = ev["key"]
            if key not in cache:
                results.append(None)
            else:
                value, _expires_at = cache[key]
                # Mark MRU
                cache.move_to_end(key, last=True)
                results.append(value)
        else:
            raise ValueError(f"Unknown op: {op}")

    return results
