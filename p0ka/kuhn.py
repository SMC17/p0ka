"""Full-tree vanilla CFR for two-player Kuhn poker.

This is a reference correctness laboratory, not a multiplayer tournament solver.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from itertools import permutations
from random import Random


@dataclass(slots=True)
class Node:
    regret: list[float] = field(default_factory=lambda: [0.0, 0.0])
    strategy_sum: list[float] = field(default_factory=lambda: [0.0, 0.0])

    def strategy(self, reach: float) -> tuple[float, float]:
        positive = [max(0.0, r) for r in self.regret]
        total = sum(positive)
        probs = (positive[0] / total, positive[1] / total) if total else (0.5, 0.5)
        for i in range(2):
            self.strategy_sum[i] += reach * probs[i]
        return probs

    def average(self) -> tuple[float, float]:
        total = sum(self.strategy_sum)
        return (self.strategy_sum[0] / total, self.strategy_sum[1] / total) if total else (0.5, 0.5)


TERMINALS = frozenset(("pp", "bp", "bb", "pbp", "pbb"))


def payoff_for_player_to_act(cards: tuple[int, int], history: str) -> int:
    if history not in TERMINALS:
        raise ValueError("not a terminal history")
    player = len(history) % 2
    if history in ("pp", "bb", "pbb"):
        win = 1 if cards[player] > cards[1 - player] else -1
        return win * (2 if history in ("bb", "pbb") else 1)
    return 1  # The previous player folded, current player wins one ante.


class KuhnCFR:
    def __init__(self) -> None:
        self.nodes: dict[tuple[int, str], Node] = {}

    def _cfr(self, cards: tuple[int, int], history: str,
             reach0: float, reach1: float) -> float:
        if history in TERMINALS:
            return payoff_for_player_to_act(cards, history)
        player = len(history) % 2
        key = (cards[player], history)
        node = self.nodes.setdefault(key, Node())
        strategy = node.strategy(reach0 if player == 0 else reach1)
        utility = [0.0, 0.0]
        for action, suffix in enumerate(("p", "b")):
            if player == 0:
                utility[action] = -self._cfr(cards, history + suffix,
                                             reach0 * strategy[action], reach1)
            else:
                utility[action] = -self._cfr(cards, history + suffix,
                                             reach0, reach1 * strategy[action])
        node_utility = sum(a * b for a, b in zip(strategy, utility))
        other_reach = reach1 if player == 0 else reach0
        for i in range(2):
            node.regret[i] += other_reach * (utility[i] - node_utility)
        return node_utility

    def train(self, iterations: int = 10_000, seed: int = 7) -> None:
        if iterations < 0:
            raise ValueError("iterations must not be negative")
        rng = Random(seed)
        decks = list(permutations((0, 1, 2), 2))
        for _ in range(iterations):
            rng.shuffle(decks)
            for deal in decks:
                self._cfr(deal, "", 1.0, 1.0)

    def policy(self) -> dict[tuple[int, str], tuple[float, float]]:
        return {key: node.average() for key, node in self.nodes.items()}


def expected_p0(policy: dict[tuple[int, str], tuple[float, float]]) -> float:
    def recurse(cards: tuple[int, int], history: str) -> float:
        if history in TERMINALS:
            value = payoff_for_player_to_act(cards, history)
            return value if len(history) % 2 == 0 else -value
        acting = len(history) % 2
        probabilities = policy.get((cards[acting], history), (0.5, 0.5))
        return sum(probabilities[i] * recurse(cards, history + suffix)
                   for i, suffix in enumerate(("p", "b")))
    deals = permutations((0, 1, 2), 2)
    return sum(recurse(cards, "") for cards in deals) / 6.0
