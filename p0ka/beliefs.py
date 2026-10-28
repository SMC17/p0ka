"""Table-local, event-idempotent Bayesian opponent and hand-range beliefs."""
from __future__ import annotations
from dataclasses import dataclass, field
from math import isfinite
from typing import Mapping

ACTIONS = ("fold", "check", "call", "bet", "raise")


@dataclass(slots=True)
class DirichletCounts:
    prior: dict[str, float]
    counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.prior or any(v <= 0 or not isfinite(v) for v in self.prior.values()):
            raise ValueError("prior weights must be finite and positive")
        self.counts = {action: 0 for action in self.prior}

    def update(self, action: str) -> None:
        if action not in self.prior:
            raise ValueError("action outside legal contextual action set")
        self.counts[action] += 1

    def predictive(self, action: str) -> float:
        if action not in self.prior:
            return 0.0
        denom = sum(self.prior.values()) + sum(self.counts.values())
        return (self.prior[action] + self.counts[action]) / denom


@dataclass(slots=True)
class TableBeliefs:
    """Opponent IDs are valid only within a single table.

    Event IDs MUST be unique within the table, ideally hand/event composite IDs.
    The prior can be derived offline from an opponent population.
    """
    table_id: str
    prior_weight: float = 1.0
    posteriors: dict[tuple[str, str], DirichletCounts] = field(default_factory=dict)
    seen_events: set[str] = field(default_factory=set)
    version: int = 0

    def observe(self, event_id: str, player_id: str, context: str,
                action: str, legal_actions: tuple[str, ...]) -> bool:
        if not event_id or not player_id or not context:
            raise ValueError("event, player and context are required")
        if action not in legal_actions or not legal_actions or len(set(legal_actions)) != len(legal_actions):
            raise ValueError("invalid contextual action set")
        if event_id in self.seen_events:
            return False
        key = (player_id, context)
        if key not in self.posteriors:
            self.posteriors[key] = DirichletCounts({a: self.prior_weight for a in legal_actions})
        elif set(self.posteriors[key].prior) != set(legal_actions):
            raise ValueError("context must have consistent legal actions")
        self.posteriors[key].update(action)
        self.seen_events.add(event_id)
        self.version += 1
        return True

    def predictive(self, player_id: str, context: str, action: str,
                   legal_actions: tuple[str, ...]) -> float:
        model = self.posteriors.get((player_id, context))
        if model is None:
            return 1.0 / len(legal_actions) if action in legal_actions else 0.0
        return model.predictive(action)

    def reset(self, table_id: str) -> None:
        self.table_id = table_id
        self.posteriors.clear()
        self.seen_events.clear()
        self.version += 1


def update_range(prior: Mapping[int, float], likelihood: Mapping[int, float],
                 blockers: frozenset[int] = frozenset()) -> dict[int, float]:
    """Normalized Bayes update. Keys are mutually exclusive *abstract* hands.

    Caller must supply card-consistent hands and the action likelihood model.
    No fallback to uniform after zero likelihood: that would fabricate evidence.
    """
    weights = {}
    for hand, probability in prior.items():
        if probability < 0 or not isfinite(probability):
            raise ValueError("invalid prior")
        like = likelihood.get(hand, 0.0)
        if not isfinite(like) or not 0 <= like <= 1:
            raise ValueError("likelihood outside [0,1]")
        if hand not in blockers and probability * like:
            weights[hand] = probability * like
    norm = sum(weights.values())
    if norm <= 0:
        raise ValueError("observation has zero model likelihood")
    return {hand: weight / norm for hand, weight in weights.items()}
