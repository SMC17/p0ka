"""Dependency-free decision-path latency benchmark (local, not sandbox proof)."""
from __future__ import annotations
from dataclasses import dataclass
from math import ceil
from time import perf_counter_ns
from typing import Callable, Sequence, TypeVar

T = TypeVar('T')


@dataclass(frozen=True, slots=True)
class LatencySummary:
    samples: int
    p50_us: float
    p99_us: float
    p999_us: float
    maximum_us: float
    exceeded_1ms: int


def measure(fn: Callable[[T], object], cases: Sequence[T], repeats: int = 100) -> LatencySummary:
    if not cases or repeats <= 0:
        raise ValueError("nonempty workload and positive repeats required")
    for case in cases:
        fn(case)
    durations = []
    for _ in range(repeats):
        for case in cases:
            start = perf_counter_ns()
            fn(case)
            durations.append(perf_counter_ns() - start)
    durations.sort()
    def percentile(p: float) -> float:
        return durations[max(0, ceil(len(durations) * p) - 1)] / 1000.0
    return LatencySummary(len(durations), percentile(.5), percentile(.99),
                          percentile(.999), durations[-1] / 1000.0,
                          sum(d >= 1_000_000 for d in durations))
