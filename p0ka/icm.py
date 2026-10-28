"""Exact, iterative Independent Chip Model (ICM) for up to modest tables.

Each nonempty-stack player has a probability of occupying each finishing rank.
No claim that static ICM is a full future-game value model.
"""
from __future__ import annotations
from math import isfinite


def icm_equity(stacks: tuple[float, ...], payouts: tuple[float, ...]) -> tuple[float, ...]:
    n = len(stacks)
    if not n or len(payouts) != n or n > 16:
        raise ValueError("1..16 players and one payout per finishing rank required")
    if any(not isfinite(x) or x < 0 for x in stacks + payouts):
        raise ValueError("stacks and payouts must be finite and nonnegative")
    if not any(stacks):
        raise ValueError("at least one positive stack required")
    active = [i for i, stack in enumerate(stacks) if stack > 0]
    # Already eliminated players do not share remaining active-player payouts.
    if len(active) == 1:
        out = [0.0] * n
        out[active[0]] = payouts[0]
        return tuple(out)
    size = 1 << len(active)
    mass = [0.0] * size
    selected = [0.0] * size
    mass[0] = 1.0
    value = [0.0] * n
    total = sum(stacks[i] for i in active)
    for mask in range(size - 1):
        p = mass[mask]
        if p == 0:
            continue
        rank = mask.bit_count()
        remaining = total - selected[mask]
        for local, player in enumerate(active):
            bit = 1 << local
            if mask & bit:
                continue
            q = p * stacks[player] / remaining
            new_mask = mask | bit
            mass[new_mask] += q
            value[player] += q * payouts[rank]
            selected[new_mask] = selected[mask] + stacks[player]
    return tuple(value)
