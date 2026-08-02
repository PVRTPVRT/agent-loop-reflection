import unittest

from ttl_lru import simulate_ttl_lru


class TtlLruTests(unittest.TestCase):
    def test_expired_mru_is_removed_even_when_lru_is_live(self) -> None:
        events = [
            {"op": "put", "key": "a", "value": "A", "ttl": 100, "time": 0},
            {"op": "put", "key": "x", "value": "X", "ttl": 2, "time": 0},
            {"op": "get", "key": "x", "time": 1},
            {"op": "put", "key": "b", "value": "B", "ttl": 100, "time": 1},
            {"op": "put", "key": "c", "value": "C", "ttl": 100, "time": 2},
            {"op": "get", "key": "a", "time": 2},
            {"op": "get", "key": "x", "time": 2},
            {"op": "get", "key": "b", "time": 2},
            {"op": "get", "key": "c", "time": 2},
        ]
        self.assertEqual(
            simulate_ttl_lru(3, events),
            ["X", "A", None, "B", "C"],
        )

    def test_get_updates_recency_before_capacity_eviction(self) -> None:
        events = [
            {"op": "put", "key": "a", "value": "A", "ttl": 10, "time": 0},
            {"op": "put", "key": "b", "value": "B", "ttl": 10, "time": 0},
            {"op": "get", "key": "a", "time": 1},
            {"op": "put", "key": "c", "value": "C", "ttl": 10, "time": 2},
            {"op": "get", "key": "b", "time": 2},
            {"op": "get", "key": "a", "time": 3},
            {"op": "get", "key": "c", "time": 3},
        ]
        self.assertEqual(simulate_ttl_lru(2, events), ["A", None, "A", "C"])

    def test_exact_expiry_boundary(self) -> None:
        events = [
            {"op": "put", "key": "a", "value": 1, "ttl": 2, "time": 0},
            {"op": "get", "key": "a", "time": 1},
            {"op": "get", "key": "a", "time": 2},
        ]
        self.assertEqual(simulate_ttl_lru(2, events), [1, None])

    def test_overwrite_resets_expiry_and_recency(self) -> None:
        events = [
            {"op": "put", "key": "a", "value": "old", "ttl": 2, "time": 0},
            {"op": "put", "key": "b", "value": "B", "ttl": 10, "time": 0},
            {"op": "put", "key": "a", "value": "new", "ttl": 10, "time": 1},
            {"op": "put", "key": "c", "value": "C", "ttl": 10, "time": 2},
            {"op": "get", "key": "a", "time": 2},
            {"op": "get", "key": "b", "time": 2},
            {"op": "get", "key": "c", "time": 2},
        ]
        self.assertEqual(simulate_ttl_lru(2, events), ["new", None, "C"])

    def test_zero_and_negative_capacity(self) -> None:
        events = [
            {"op": "put", "key": "a", "value": 1, "ttl": 10, "time": 0},
            {"op": "get", "key": "a", "time": 0},
        ]
        self.assertEqual(simulate_ttl_lru(0, events), [None])
        with self.assertRaises(ValueError):
            simulate_ttl_lru(-1, [])


if __name__ == "__main__":
    unittest.main()