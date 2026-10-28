# p0ka Architecture and Decision Record (2026-10-27)

## Objective

Maximize expected Sequoia placement points with legal decisions under the one-millisecond, one-hundred-megabyte, Python-Agent constraints, not raw chip EV. Variant and payout structure are undisclosed until event day. Public rules: https://pokerbot.sequoiacap.com/rules.html

**Status:** This repository is an offline research baseline. No organizer-approved competition agent, seeded eight-player tournament benchmark, or confirmed native-extension permission exists yet.

## Invariants

1. Rules-correctness precedes strategic optimization. Raise min/max and amount interpretation must come from the official API.
2. Hidden cards are hidden. Search may sample them only as hypothetical states, never as observations to the agent.
3. History cannot be merged merely because the visible board and pot are equal; betting history changes beliefs.
4. Every opponent-statistic update requires an identifiable context/opportunity and an idempotent event ID. Reset per table.
5. Chip accounting conserves chips through main pot, side pots, tie splits, uncalled refunds and blind/ante collection.
6. All deployment choices are benchmarked on the intended interpreter and game variant, including cold-start and tail latency.
7. Complex modules are admitted into the bot only if controlled tournament experiments demonstrate positive score contribution.

## Layers

### Exact rules and state

- Hand evaluator and colex/canonical indices: `cards.py`.
- Pot settlement, odd chips, refunds: `pots.py`.
- ICM subset DP for survivor settlement: `icm.py`.
- No private-card `Agent` adapter exists until the official interface is available.

### Bayesian beliefs and computation reuse

- Context-specific Dirichlet action models and Bayesian range updates: `beliefs.py`.
- Stable state digests and versioned, bounded transposition cache: `graph.py`.
- Long-lived game state should be divided into hand, table and persistent solver state; table identity must reset.
- A hash collision is never enough to justify a strategic merge; the full key is checked.
- Approximate compression or data-dependent transposition merges require labeled error budgets.

### Decision and tournament value

- `policy.py` demonstrates action validation and a safe reference, not a GTO or optimized tournament decision policy.
- Immediate decision estimates are calibrated from rule-specific equity and ranges.
- At high stakes, optimize estimated **terminal placement reward** using a future-game value proxy with a static ICM fallback.
- All-in losses, risk premiums and blind pressure must be validated against the official payout and blind schedule.
- Online search must maintain a legal fallback and return early if uncertainty is not worth further computation.

### Research and validation

- `kuhn.py` validates two-player CFR implementation against the known Kuhn game value (-1/18 for player zero); it does not certify multiway equilibrium.
- `equity.py` gives reproducible reference Monte Carlo equity for two-hole high-hand variants with uniformly sampled opponents; it is intentionally not a production policy.
- `benchmark.py` reports latency percentiles, but its local results do not guarantee official sandbox compliance.
- Future simulation should include opponent mixtures, paired seeds, confidence intervals and variant holdouts.

## Search and AI research program

Order by empirical value and engineering feasibility:

1. Offline equilibrium references (Kuhn/Leduc CFR+, external-sampling MCCFR, multiplayer self-play baselines).
2. Exact card-bucket features and range-conditioned equity; quantization and suit-isomorphic canonicalization.
3. Bayesian fold/call/raise likelihoods conditioned on legal actions, position, phase, pot odds and stack.
4. Robust policy vs opponent population; evaluate strategy exploitation under model uncertainty.
5. Static ICM and learned correction for future blinds and 200-hand terminal cutoff.
6. Bounded, belief-consistent action refinement; avoid naive perfect-information determinization.
7. Offline CFR/RL teacher -> small distilled policy, with held-out tournament score and latency gates.
8. Native C++/Zig evaluators only when permitted by the event and measurably faster end-to-end.

## Immediate go/no-go tests

- **Compatibility:** Official interface, lifecycle, expected output, permitted extensions and libraries; halt deployment assumptions until resolved.
- **Rules:** Differential cross-check of 5-card, 7-card, Omaha, short deck, full house/flush inversion, high/low rules if needed, side pots and odd-chip allocation.
- **Tail:** P50/P99/P99.9, cold/steady-state, full adapter marshaling; no invalid action or timeout in randomized stress suite.
- **Opponent:** Compare baseline to Bayesian variant across held-out opponent populations; reject statistically weak improvements.
- **Utility:** Optimize realized placement points, not only chip-EV, chip counts or hand equity.

## Honest limitations

There are no real Sequoia observations or validated winning policies in this repository. The project currently contains mathematical building blocks, not the complete solution; selected abstractions, training assets and contest-compliant deployment remain work to do.
