# p0ka

**Variant-aware poker research foundation, not a finished Sequoia submission.**

`p0ka` begins with auditable primitives for poker research: configurable five-card rankings and Omaha-style selection constraints, colex combinatorial indices, suit-symmetric card canonicalization, exact eight-player ICM via subset dynamic programming, table-local Bayesian opponent counters, belief-versioned transposition caching, a legal-action-safe reference policy, and two-player Kuhn CFR as a game-theory correctness laboratory. It also includes exact reference side-pot settlement, uniform-range Monte Carlo equity, and local latency measurements.

## Quickstart

Requires Python 3.11+; the current core has no runtime third-party dependencies.

```bash
python -m unittest discover -s tests -v
python -m p0ka
```

This does **not** implement the unreleased Sequoia tournament `Agent` interface, and the reference hand evaluator and CFR lab are **not** guaranteed to finish within the event's one-millisecond decision deadline. The internal DTO deliberately does not guess submission schema or raise amount semantics.

## Module contracts

| Module | Purpose | Limits |
| --- | --- | --- |
| `cards.py` | Exact 5-card high evaluation, best-5 selection, short-deck ranking switches, Omaha selection, suit canonicalization, combinadic indexing | Reference path, not microsecond evaluator. Variant-specific hand ranks need explicit rules. |
| `icm.py` | Exact Independent Chip Model using subset DP (up to 16 active players) | Not a future-game, stack-dynamics or blind-escalation model; already-eliminated payouts handled externally. |
| `beliefs.py` | Table-scoped idempotent action counters, Dirichlet predictive probabilities, Bayes hand-range update | Requires stable table/hand event IDs, accurate legal action contexts, and externally provided likelihoods; range keys represent disjoint abstract hands. |
| `graph.py` | 128-bit digests with full-key collision verification and belief-version cache isolation | A cache, not a claim of strategic equivalence or a full public belief-state DAG. |
| `policy.py` | Action validation, error-safe fallback, simple pot-odds policy | Deliberately weak baseline; no opponent range or full tournament utility. Must map to official API once revealed. |
| `kuhn.py` | Full-tree vanilla CFR, policy extraction, exact expected return in Kuhn poker | Two-player toy zero-sum, **not** an eight-player solver. |
| `equity.py` | Seeded, uniform-opponent Monte Carlo equity and fractional tie payouts | Offline reference only; no realistic range priors and not guaranteed under 1 ms. |
| `pots.py` | Side pots, ties, folded chips, odd chips, unmatched refunds | Caller supplies correct showdown ranks and official odd-chip seat order. |
| `benchmark.py` | Warm-path latency percentiles and timeout counts | Local measurement only; no guarantee of official sandbox timing. |

## Research-to-deployment architecture

```text
Official unknown variant specification + starter kit
  -> rules/configuration and conformance fixtures
  -> exact public/private information-state reconstruction
  -> evaluator / likelihood / table-posterior primitives
  -> baseline policy + tournament utility
  -> selective small compute, if tested and profitable
  -> official Agent adapter + hard-deadline legal fallback

Separate offline pipeline:
  variant simulator -> opponent population -> CFR/RL experiments
  -> statistically powered tournaments -> policy distillation
  -> benchmarked, permission-compliant deployment artifacts
```

## Competition constraints / compliance

According to the public Sequoia competition rules (October 2026), the variant and Agent interface are disclosed during the **60-minute build**; bot decisions must finish within **1 ms**, artifacts must be **<=100 MB**, state resets each table, and the scoring objective is weighted average *placement points* across six tournaments of 10,000 eight-player sit-and-gos. Public rules do **not clearly authorize** use of custom prewritten libraries or precomputed strategy artifacts. Clarify this with organizers before submitting any part of this repository. Do not connect a live bot to outside services or persist opponent identification across tables.

Rules: https://pokerbot.sequoiacap.com/rules.html

## Next milestones (ordered)

1. **P0: Obtain official starter kit.** Implement a separately tested adapter for the exact `Agent` lifecycle, legal actions, input schema, and state persistence behavior. No schema guesses.
2. **P0: Correctness frontier.** Property and differential tests for side pots, odd chips, dealer/blind rules, refunds, split pots, showdowns, all supported hand rankings, and tournament scores. Cross-check PokerKit / OpenSpiel reference engines offline, respecting licenses.
3. **P0: Throughput frontier.** Add bounded latency harness measuring end-to-end cold and warm P50/P99/P99.9 on the *actual* sandbox. Replace combinational reference evaluator with a verified native or compact-table evaluator **only if allowed**.
4. **P1: Real policy frontier.** Range-aware equity, blockers and correlated multiway ranges, calibrated opponent action priors, survival-adjusted placement utility, short-stack action logic, and action/bet-size abstraction.
5. **P1: Arena.** Seeded multiway simulation, realistic opponent mixtures, paired-seed comparisons, confidence intervals, stress testing and scenario coverage. Improve policy only with held-out placement-score evidence.
6. **P2: Advanced research.** DCFR/MCCFR baselines on tractable variants, belief-aware subgame resolution, adversarial opponent search, policy/value distillation, learned opponent embeddings and bounded search-budget control. Deploy only measured benefits.

### Design guardrails

- Never merge game histories simply because their public cards and pot sizes match. Information-state keys must preserve relevant recall and posterior versions.
- For actions without a contextual legal-action model, preserve a legal fallback rather than invent a response.
- Tournament value is expected **placement points**, not purely chip EV; static ICM is a useful diagnostic, not a complete terminal-outcome predictor.
- The evaluation of a simulated opponent must never use their private cards as if the acting bot observed them.
- The actual game may change rankings, betting phases, action types and hand selection rules. No broad claim of universality is made.

## Development status

Initial research core with unit tests; no real variant integration, trained strategies, opponent tournaments, official sandbox benchmarking, or quantified competitive performance yet.
