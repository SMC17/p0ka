"""Exact reference hand evaluator and collision-free card indexing.

Correctness-oriented: combinational best-hand evaluation is not the 1 ms hot path.
Rules explicitly represent the hand-selection and ranking differences tested here.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from functools import lru_cache
from itertools import combinations, permutations
from math import comb

RANKS = "23456789TJQKA"
SUITS = "shdc"


@dataclass(frozen=True, order=True, slots=True)
class Card:
    rank: int
    suit: int

    def __post_init__(self) -> None:
        if not (2 <= self.rank <= 14 and 0 <= self.suit < 4):
            raise ValueError("invalid standard card")

    @classmethod
    def parse(cls, text: str) -> Card:
        if len(text) != 2 or text[0].upper() not in RANKS or text[1].lower() not in SUITS:
            raise ValueError(f"invalid card {text!r}")
        return cls(RANKS.index(text[0].upper()) + 2, SUITS.index(text[1].lower()))

    @property
    def id(self) -> int:
        return (self.rank - 2) * 4 + self.suit


@dataclass(frozen=True, slots=True)
class HandRules:
    """Rules for high-hand evaluation. Other poker variants require new evaluators."""
    min_rank: int = 2
    exact_hole: int | None = None  # None: best five from union; Omaha: 2
    exact_board: int | None = None  # Omaha: 3
    flush_over_full_house: bool = False
    trips_over_straight: bool = False

    def __post_init__(self) -> None:
        if not 2 <= self.min_rank <= 10:
            raise ValueError("min_rank must be between 2 and 10")
        if (self.exact_hole is None) != (self.exact_board is None):
            raise ValueError("hole and board selection must be specified together")
        if self.exact_hole is not None and self.exact_hole + self.exact_board != 5:
            raise ValueError("exact card selections must total five")


STANDARD = HandRules()
SHORT_DECK = HandRules(min_rank=6, flush_over_full_house=True)
OMAHA = HandRules(exact_hole=2, exact_board=3)


def _validate(cards: tuple[Card, ...], rules: HandRules) -> None:
    if len(set(cards)) != len(cards):
        raise ValueError("duplicate cards")
    if any(c.rank < rules.min_rank for c in cards):
        raise ValueError("card is not in this variant's deck")


def _straight_high(ranks: set[int], min_rank: int) -> int:
    for high in range(14, min_rank + 3, -1):
        if all(high - i in ranks for i in range(5)):
            return high
    # A-2-3-4-5 in standard, A-6-7-8-9 in 36-card short deck.
    wheel = {14, *range(min_rank, min_rank + 4)}
    return min_rank + 3 if wheel.issubset(ranks) else 0


@lru_cache(maxsize=100_000)
def _eval_five_cached(cards: tuple[Card, ...], rules: HandRules) -> tuple[int, ...]:
    counts = Counter(c.rank for c in cards)
    by_count = sorted(((n, r) for r, n in counts.items()), reverse=True)
    rank_list = sorted((c.rank for c in cards), reverse=True)
    flush = len({c.suit for c in cards}) == 1
    straight = _straight_high(set(rank_list), rules.min_rank)
    full_cat = 5 if rules.flush_over_full_house else 6
    flush_cat = 6 if rules.flush_over_full_house else 5
    trips_cat = 4 if rules.trips_over_straight else 3
    straight_cat = 3 if rules.trips_over_straight else 4
    if straight and flush:
        return (8, straight)
    if by_count[0][0] == 4:
        return (7, by_count[0][1], by_count[1][1])
    if by_count[0][0] == 3 and by_count[1][0] == 2:
        return (full_cat, by_count[0][1], by_count[1][1])
    if flush:
        return (flush_cat, *rank_list)
    if straight:
        return (straight_cat, straight)
    if by_count[0][0] == 3:
        return (trips_cat, by_count[0][1], *sorted((r for r in counts if r != by_count[0][1]), reverse=True))
    pairs = sorted((r for r, n in counts.items() if n == 2), reverse=True)
    if len(pairs) == 2:
        return (2, *pairs, next(r for r, n in counts.items() if n == 1))
    if len(pairs) == 1:
        return (1, pairs[0], *sorted((r for r in counts if r != pairs[0]), reverse=True))
    return (0, *rank_list)


def evaluate_five(cards: tuple[Card, ...], rules: HandRules = STANDARD) -> tuple[int, ...]:
    if len(cards) != 5:
        raise ValueError("evaluate_five requires exactly five cards")
    _validate(cards, rules)
    return _eval_five_cached(tuple(sorted(cards)), rules)


def evaluate_best(
    hole: tuple[Card, ...], board: tuple[Card, ...], rules: HandRules = STANDARD
) -> tuple[int, ...]:
    all_cards = hole + board
    _validate(all_cards, rules)
    if len(all_cards) < 5:
        raise ValueError("at least five total cards required")
    if rules.exact_hole is None:
        hands = combinations(all_cards, 5)
    else:
        if len(hole) < rules.exact_hole or len(board) < rules.exact_board:
            raise ValueError("insufficient private or public cards")
        hands = (h + b for h in combinations(hole, rules.exact_hole)
                 for b in combinations(board, rules.exact_board))
    return max(_eval_five_cached(tuple(sorted(hand)), rules) for hand in hands)


def combinadic_rank(ids: tuple[int, ...], deck_size: int = 52) -> int:
    """Unique colex rank of an unordered fixed-size card subset."""
    if len(set(ids)) != len(ids) or any(i < 0 or i >= deck_size for i in ids):
        raise ValueError("invalid card indices")
    return sum(comb(card, index + 1) for index, card in enumerate(sorted(ids)))


def canonical_cards(
    private: tuple[Card, ...], public_groups: tuple[tuple[Card, ...], ...]
) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Canonical suit-isomorphism key preserving private/public *groups*.

    Safe for suit-symmetric cards, not for arbitrary game state or betting history.
    Group order preserves street boundaries. Within groups, cards are unordered.
    """
    cards = private + tuple(c for group in public_groups for c in group)
    if len(set(cards)) != len(cards):
        raise ValueError("duplicate cards")
    best = None
    for perm in permutations(range(4)):
        encoded = tuple(
            tuple(sorted((c.rank, perm[c.suit]) for c in group))
            for group in (private, *public_groups)
        )
        if best is None or encoded < best:
            best = encoded
    return best if best is not None else ((),)
