"""Typed, bounded transposition cache with explicit belief invalidation.

Only pure hand/rules computations are safely cacheable without belief versions.
A digest is a lookup accelerator, not a proof that strategic states are equivalent.
"""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from hashlib import blake2b
from json import dumps
from typing import Any


@dataclass(frozen=True, slots=True)
class StateKey:
    variant: str
    public_state: tuple[Any, ...]
    private_info: tuple[Any, ...]
    history_summary: tuple[Any, ...]
    belief_version: int

    def digest(self) -> bytes:
        # Canonical primitive tuples only; never include unsorted maps or objects.
        payload = dumps((self.variant, self.public_state, self.private_info,
                         self.history_summary, self.belief_version),
                        separators=(",", ":"), allow_nan=False)
        return blake2b(payload.encode(), digest_size=16).digest()


class TranspositionCache:
    def __init__(self, capacity: int = 4096):
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data: OrderedDict[bytes, tuple[StateKey, Any]] = OrderedDict()

    def get(self, key: StateKey) -> Any | None:
        item = self._data.get(key.digest())
        if item is None or item[0] != key:
            return None  # Store original key, defending against hash collision.
        self._data.move_to_end(key.digest())
        return item[1]

    def put(self, key: StateKey, value: Any) -> None:
        digest = key.digest()
        self._data[digest] = (key, value)
        self._data.move_to_end(digest)
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)
