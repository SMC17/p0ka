"""Reference side-pot settlement with eligibility, tie splitting, and refunds.

Does not impose a variant's betting rules. Any unmatched contribution is returned
rather than counted as a contested pot. Odd-chip order must match the rulebook.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settlement:
    awards: tuple[int, ...]    # Chips won from contested pots
    refunds: tuple[int, ...]   # Unmatched bets returned


def settle_pots(
    contributed: tuple[int, ...],
    eligible: tuple[bool, ...],
    ranks: tuple[tuple[int, ...] | None, ...],
    odd_chip_order: tuple[int, ...] | None = None,
) -> Settlement:
    """Settle pots using lexicographically comparable exact showdown ranks.

    `eligible=False` means folded, but the seat's contribution stays in pots.
    `odd_chip_order` lists all seat IDs in tie-breaking award priority order.
    The official variant must specify which seat receives odd chips.
    """
    n = len(contributed)
    if not n or len(eligible) != n or len(ranks) != n:
        raise ValueError("contribution, eligibility and rank sizes must match")
    if any(not isinstance(c, int) or c < 0 for c in contributed):
        raise ValueError("contributions must be nonnegative integers")
    if any(eligible[i] and ranks[i] is None for i in range(n)):
        raise ValueError("eligible showdown seat missing rank")
    if odd_chip_order is None:
        odd_chip_order = tuple(range(n))
    if sorted(odd_chip_order) != list(range(n)):
        raise ValueError("odd-chip ordering must be a permutation of seats")
    order = {seat: i for i, seat in enumerate(odd_chip_order)}
    awards, refunds = [0] * n, [0] * n
    levels = sorted(set(x for x in contributed if x > 0))
    previous = 0
    for level in levels:
        contributors = [i for i, c in enumerate(contributed) if c >= level]
        amount = (level - previous) * len(contributors)
        previous = level
        if len(contributors) == 1:
            refunds[contributors[0]] += amount
            continue
        participants = [i for i in contributors if eligible[i]]
        if not participants:
            raise ValueError("pot has no eligible winner: inconsistent game history")
        best = max(ranks[i] for i in participants)
        winners = sorted((i for i in participants if ranks[i] == best), key=order.get)
        common, remainder = divmod(amount, len(winners))
        for i, winner in enumerate(winners):
            awards[winner] += common + (1 if i < remainder else 0)
    if sum(awards) + sum(refunds) != sum(contributed):
        raise AssertionError("chip conservation violation")
    return Settlement(tuple(awards), tuple(refunds))
