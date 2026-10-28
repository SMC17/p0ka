"""Uniform-range Monte Carlo equity reference, for OFFLINE analysis only.

This intentionally does not claim to model opponent ranges or satisfy a 1 ms
competition deadline. It is a correctness baseline for later range-weighted
and native implementations. Split pots are credited fractionally.
"""
from __future__ import annotations
from dataclasses import dataclass
from random import Random

from .cards import Card, HandRules, STANDARD, evaluate_best


@dataclass(frozen=True, slots=True)
class EquityEstimate:
    trials: int
    equity: float
    sole_wins: int
    tied_first: int


def uniform_equity(
    hero: tuple[Card, Card],
    board: tuple[Card, ...] = (),
    opponents: int = 1,
    trials: int = 1000,
    seed: int = 7,
    rules: HandRules = STANDARD,
) -> EquityEstimate:
    """Evaluate two-hole-card community games with unknown uniform hands.

    For Omaha, auction, draw, split-pot or constrained ranges, a different
    sampler and terminal utility are required. Do not use for those variants.
    """
    if rules.exact_hole is not None:
        raise ValueError("exact-hole games require another sampling model")
    if len(hero) != 2 or len(board) > 5 or opponents < 1 or trials < 1:
        raise ValueError("invalid hole, board, opponent count or trial count")
    known = hero + board
    if len(set(known)) != len(known):
        raise ValueError("duplicate known cards")
    if any(c.rank < rules.min_rank for c in known):
        raise ValueError("card excluded from variant deck")
    deck = [Card(rank, suit) for rank in range(rules.min_rank, 15) for suit in range(4)
            if Card(rank, suit) not in known]
    count = (5 - len(board)) + opponents * 2
    if count > len(deck):
        raise ValueError("not enough remaining cards")
    rng = Random(seed)
    equity = 0.0
    sole_wins = tied_first = 0
    for _ in range(trials):
        sampled = rng.sample(deck, count)
        board_full = board + tuple(sampled[:5-len(board)])
        hero_rank = evaluate_best(hero, board_full, rules)
        winner_count = 1
        better = False
        for j in range(opponents):
            start = 5 - len(board) + 2*j
            opp_rank = evaluate_best(tuple(sampled[start:start+2]), board_full, rules)
            if opp_rank > hero_rank:
                better = True
                break
            if opp_rank == hero_rank:
                winner_count += 1
        if not better:
            equity += 1.0 / winner_count
            if winner_count == 1:
                sole_wins += 1
            else:
                tied_first += 1
    return EquityEstimate(trials, equity / trials, sole_wins, tied_first)
