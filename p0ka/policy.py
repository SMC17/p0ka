"""Safe, minimal tournament policy reference; NOT a competitive finished agent.

No unreleased tournament API is guessed here. Observation is an internal DTO.
The caller owns equity estimation and variant-specific action semantics.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class Action:
    kind: str  # fold/check/call/raise, other variants need adapters
    minimum: int = 0
    maximum: int = 0

    def __post_init__(self) -> None:
        if self.minimum < 0 or self.maximum < self.minimum:
            raise ValueError("invalid amount bounds")


@dataclass(frozen=True, slots=True)
class Decision:
    kind: str
    amount: int = 0


@dataclass(frozen=True, slots=True)
class Observation:
    legal: tuple[Action, ...]
    pot: int
    to_call: int
    equity: float | None = None
    risk_premium: float = 0.0

    def __post_init__(self) -> None:
        if self.pot < 0 or self.to_call < 0 or not self.legal:
            raise ValueError("invalid pot, cost or actions")
        if self.equity is not None and (not isfinite(self.equity) or not 0 <= self.equity <= 1):
            raise ValueError("equity must be in [0,1]")
        if not isfinite(self.risk_premium) or not 0 <= self.risk_premium < 1:
            raise ValueError("risk_premium must be in [0,1)")


def validate_decision(decision: Decision, legal: tuple[Action, ...]) -> bool:
    return any(a.kind == decision.kind and a.minimum <= decision.amount <= a.maximum
               for a in legal)


def fallback(legal: tuple[Action, ...]) -> Decision:
    """Prefer free check, then fold, then call, else minimum legal action."""
    for name in ("check", "fold", "call"):
        for action in legal:
            if action.kind == name:
                return Decision(name, action.minimum)
    return Decision(legal[0].kind, legal[0].minimum)


def choose_action(obs: Observation) -> Decision:
    """Correctly bounded reference policy, deliberately not labeled GTO.

    Assumes pot includes existing commitments and a call adds to_call to pot.
    Exact game semantics must be checked against official rules before use.
    """
    legal = {a.kind: a for a in obs.legal}
    if "check" in legal:
        # No rationale to fold if checking is free; optional value bet when strong.
        if obs.equity is not None and obs.equity > .80 and "raise" in legal:
            bet = legal["raise"]
            result = Decision("raise", max(bet.minimum, min(bet.maximum, obs.pot // 2)))
            if validate_decision(result, obs.legal):
                return result
        return Decision("check", legal["check"].minimum)
    if obs.equity is None:
        return fallback(obs.legal)
    # Simplified pot odds. Future actions and multiway effects are unmodeled.
    threshold = obs.to_call / (obs.pot + obs.to_call) if obs.pot + obs.to_call else 1.0
    threshold = min(1.0, threshold + obs.risk_premium)
    if obs.equity < threshold and "fold" in legal:
        return Decision("fold", legal["fold"].minimum)
    if "call" in legal:
        return Decision("call", legal["call"].minimum)
    return fallback(obs.legal)
