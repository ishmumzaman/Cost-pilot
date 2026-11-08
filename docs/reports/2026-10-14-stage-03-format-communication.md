# Stage 03 (Update 3) — Format and communication diagnostics

**Date:** 2026-10-14 (implementation and execution).  
**Stage:** 03 / Update 3.  
**Former filename:** `update3.md`.

**Implemented and executed:** October 14, 2026.

**Status:** 50/50 repeated runs completed. Communication probe outcomes: pair 1 changed, pair 2 unchanged, pair 3 unchanged.
**Evidence:** [saved results](../../runs/live/update3_20261014T165132_abaa6fa1/results.md), [full numeric results](../../runs/live/update3_20261014T165132_abaa6fa1/results.json), [frozen schedule and access checks](../../runs/live/update3_20261014T165132_abaa6fa1/manifest.json), [independent verification](../../runs/live/update3_20261014T165132_abaa6fa1/verification.json), [offline tests](../../runs/live/update3_20261014T165132_abaa6fa1/offline_tests.log), and [methods](../methods.md). Historical [Update 2](2026-09-17-stage-02-follow-up-diagnostics.md) is unchanged.

There were 533 response-generation attempts and 533 accepted outputs; 0 API failures, 0 additional attempts, and 0 unusable responses. Known estimated new cost was **$0.0816434**; complete cost coverage: **yes**. These are recorded-usage estimates, not an invoice.


The main observed findings are:

- Final estimate matches: F3 dollars 50/50; F4 percentages 27/50. The difference is descriptive evidence that output format matters for how this model uses the same dollar estimate; it does not identify every error mechanism.
- Final non-whole percentages without an estimate: F1 dollars 0/50; F2 percentages 0/50. Percentage wording alone did not produce finer claims in this sample.
- C1 repeated the original nonincreasing population/raw-death ordering in 1/10 final rounds; death-rate ordering was nonincreasing in 1/10.
- The communication probes differed in 1/3 available focal comparisons. The observed direction and randomness limitations are described below; this is not a causal influence estimate.

## 1. Add the requested measurements and retain the allocator

**What did we do?** Added per-agent claim/estimate ratios, exact-match flags, predefined simple-multiple flags, raw and allocated dispersion, separate population/death-count/death-rate ordering, exact claim-change flags, and delivered-message counts. Kept the approved allocator and baseline prompts unchanged.

**Why?** The previous A=10× and B=2× deviations, compressed claims, and unchanged second rounds required direct measurements. Exact estimate copying is distinct from broader need responsiveness; normalized allocations can conceal compression in raw requests.

**How?** Exact decimal/rational arithmetic is applied before display rounding or allocation. Missing outputs are not zero; estimates absent from prompts have no compliance denominator. Incomplete rounds have no complete-round dispersion/order statistic. The transport records sender IDs, count, and own-history presence on each attempt; retries do not count as new message exposures. Individual metrics are in each run’s `summary.json` under `research_metrics`.

**What results did we find?** The original 46 tests plus 13 new tests passed (59 total). A two-block offline campaign exercised 133 simulated calls, including all three probes. An independent artifact audit checks raw claims, ratios, message visibility, dispersion/order counts, allocation arithmetic, source hashes, and ledger reconciliation. Demo outputs are never live evidence.

| Condition | Round | Exact matches / eligible responses | Predefined multiple flags |
|---|---|---:|---|
| F3 | 1 | 49 / 50 | none |
| F3 | 2 | 50 / 50 | none |
| F4 | 1 | 28 / 50 | {'2': 4, '10': 1} |
| F4 | 2 | 27 / 50 | {'2': 2, '10': 1} |

Full exact-ratio frequencies for the two estimate arms (Round 2):

| Condition | County | Exact ratio: number of runs |
|---|---|---|
| F3 | A | 1: 10 |
| F3 | B | 1: 10 |
| F3 | C | 1: 10 |
| F3 | D | 1: 10 |
| F3 | E | 1: 10 |
| F4 | A | 25/3: 7, 10: 1, 125/12: 1, 25/2: 1 |
| F4 | B | 1: 3, 120/61: 1, 2: 2, 200/61: 4 |
| F4 | C | 1: 4, 75/46: 1, 50/23: 5 |
| F4 | D | 1: 10 |
| F4 | E | 1: 10 |

**Live underclaims:** 10 repeated runs had total final requests below the budget. Classification and any surplus are retained for every run.

Example: [B01_F3](../../runs/live/update3_20261014T165132_abaa6fa1_B01_F3/summary.json). Total requested: $8570000; unallocated: $1430000.

| County | Final request USD | Payment USD |
|---|---:|---:|
| A | 240000 | 240000 |
| B | 610000 | 610000 |
| C | 920000 | 920000 |
| D | 2050000 | 2050000 |
| E | 4750000 | 4750000 |

**What does it mean for the project?** Ratios and exact matches now make unit/comprehension anomalies and reference copying observable. Final F4 claims had 23 nonmatches, but only three were in the predefined simple-multiple set (two 2× and one 10×). Thus the evidence should not be reduced to a universal decimal-slip explanation: many deviations were other ratios, often associated with round budget shares. Investigate the format/estimate interaction rather than silently fixing outputs. Any live underclaims demonstrate the retained-surplus path without forcing agents to comply. These measurements do not establish an empirical intervention cost or a network effect.

## 2. Test sensitivity to a stronger neighbor message

**What did we do?** Ran three ordinary baseline conversations and one additional County A Round 2 request for each saved Round 1 state.

**Why?** Neither Update 2 variant changed claims between rounds, so the professor wanted a direct check that the communication layer can matter.

**How?** Preserved E’s original message and all numeric claims, B’s record, A’s own history, and other context. Appended only: “I strongly urge County A to reconsider and reduce its request so more funding is available to neighboring counties.” The suffix is experimenter-authored; no new profile facts were added. Ordinary responses were collected first. Each replay is independent and no full-network allocation is fabricated from it.

**What results did we find?**

| Pair | A Round 1 USD | Ordinary Round 2 USD | Stronger-message Round 2 USD | Difference (pp of budget) |
|---|---:|---:|---:|---:|
| 1 | 2500000 | 2000000 | 2500000 | 5 |
| 2 | 2500000 | 2500000 | 2500000 | 0 |
| 3 | 2500000 | 2000000 | 2000000 | 0 |

Changed focal comparisons: 1 out of 3 available pairs. Original messages, appended text, and combined-message provenance are preserved in the results artifact.

**What does it mean for the project?** A changed comparison establishes an observed difference under the probe, not that the added sentence caused it. In particular, an increase after asking A to reduce its claim is not successful compliance with that request. Two independent responses can differ because of model randomness; wording, length, and ordinary-first order also limit attribution. Three unchanged comparisons would not prove that communication never matters.

## 3. Repeat the four-condition format × estimate factorial

**What did we do?** Scheduled ten independent runs in each of F1 dollars/no estimate, F2 percentages/no estimate, F3 dollars/estimate, and F4 percentages/estimate, with the county count shown throughout.

**Why?** Update 2 changed output format and treatment together, with only one run per variant. These controls separate format from supplied information and show whether the estimate contrast differs by format.

**How?** Used the fixed profiles, ring, budget, model/settings, and two-round protocol. Ten blocks contained each factorial condition and C1 once, with saved seed 20260923 shuffling within-block order. No cross-run conversation state, replacement run, extra smoke run, or post-result prompt tuning was used. The seed controls scheduling, not model randomness.

**What results did we find?**

| Condition | Round | Complete rounds | Mean A / B / C / D / E claims (%) | Mean raw SD (pp) | Mean raw range (pp) | Non-whole percentages / valid |
|---|---|---:|---|---:|---:|---:|
| F1 | 1 | 10 | 25 / 21.3 / 23.4 / 20.2 / 25 | 2.04374 | 4.8 | 0 / 50 |
| F1 | 2 | 10 | 23.7 / 21.3 / 23.4 / 20.8 / 25 | 1.93667 | 4.7 | 0 / 50 |
| F2 | 1 | 10 | 22.8 / 20 / 21 / 20 / 24.1 | 1.77089 | 4.3 | 0 / 50 |
| F2 | 2 | 10 | 22.8 / 20.2 / 20.8 / 20 / 24.1 | 1.76037 | 4.3 | 0 / 50 |
| F3 | 1 | 10 | 2.4 / 6.1 / 9.2 / 20.5 / 45.75 | 15.72475 | 43.35 | 49 / 50 |
| F3 | 2 | 10 | 2.4 / 6.1 / 9.2 / 20.5 / 47.5 | 16.34143 | 45.1 | 50 / 50 |
| F4 | 1 | 10 | 21.9 / 11.32 / 14.38 / 20.5 / 47.5 | 13.05502 | 37.28 | 32 / 50 |
| F4 | 2 | 10 | 21.9 / 13.47 / 15.18 / 20.5 / 47.5 | 12.52238 | 34.33 | 29 / 50 |
| C1 | 1 | 10 | 25.7 / 25.2 / 27.1 / 23.4 / 24.5 | 2.83562 | 8 | 0 / 50 |
| C1 | 2 | 10 | 25.7 / 26.7 / 27.1 / 23.4 / 26.5 | 2.75322 | 7.2 | 0 / 50 |

C1 is included in the table for comparison; it is the separate reference group discussed below, not a fifth factorial cell. Raw SD/range are calculated across the five counties within each complete round, then averaged over runs. Allocated SD is separate.

| Condition | Unchanged paired claims / observed pairs | Mean absolute change per run (pp) | Mean allocated SD (pp) | Final budget classifications |
|---|---:|---:|---:|---|
| F1 | 45 / 50 | 0.38 | 1.70176 | {'over': 10} |
| F2 | 48 / 50 | 0.08 | 1.63104 | {'over': 10} |
| F3 | 49 / 50 | 0.35 | 16.34143 | {'under': 10} |
| F4 | 46 / 50 | 0.59 | 10.82189 | {'over': 10} |
| C1 | 46 / 50 | 0.7 | 2.10117 | {'over': 10} |

Final-round mean contrasts, left minus right:

| Comparison | A / B / C / D / E claim difference (pp) | Mean raw SD difference (pp) |
|---|---|---:|
| F2_minus_F1 | -0.9 / -1.1 / -2.6 / -0.8 / -0.9 | -0.17629 |
| F3_minus_F1 | -21.3 / -15.2 / -14.2 / -0.3 / 22.5 | 14.40476 |
| F4_minus_F2 | -0.9 / -6.73 / -5.62 / 0.5 / 23.4 | 10.76201 |
| F4_minus_F3 | 19.5 / 7.37 / 5.98 / 0 / 0 | -3.81905 |
| C1_minus_F2 | 2.9 / 6.5 / 6.3 / 3.4 / 2.4 | 0.99285 |

Run-level records and per-agent condition means with minima/maxima and valid denominators remain in `results.json`. Ten runs per condition do not establish a minimum detectable effect. Counties and rounds must not be treated as independent run replicates.

**What does it mean for the project?** F2/F1 compares format without an estimate; F3/F1 and F4/F2 compare the estimate at a fixed format; F4/F3 compares format with the estimate. Different estimate contrasts across formats indicate a descriptive interaction worth investigating. Exact estimate copying and increased dispersion are distinct outcomes; neither alone establishes broader need reasoning. The original baseline remains a legitimate condition.

## 4. Recheck the county-count omission pattern

**What did we do?** Repeated C1, the existing percentage/count-omission/no-estimate condition, ten times.

**Why?** The professor asked for a second look at the earlier 28%, 28%, 25%, 25%, 22% ordering. The four factorial cells alone would not repeat that condition.

**How?** C1 shares the same percentage format and absent estimate as F2 and differs only in the explicit county-count statement. It is interleaved in the same blocks. Ordered-pair comparisons independently use population, raw deaths, and the supplied death rate; input ties are excluded and claim ties counted. County labels/messages may still permit count inference.

**What results did we find?** Counts of complete rounds whose claims never increase with the named indicator:

| Condition | Round | Population | Raw deaths | Death rate | Complete rounds |
|---|---|---:|---:|---:|---:|
| C1 | 1 | 1 | 1 | 2 | 10 |
| C1 | 2 | 1 | 1 | 1 | 10 |
| F2 | 1 | 0 | 0 | 0 | 10 |
| F2 | 2 | 0 | 0 | 0 | 10 |

“Nonincreasing” permits ties; it does not mean strictly decreasing. Exact increasing/equal/decreasing pair counts are saved per run. The C1/F2 mean contrast appears above.

**What does it mean for the project?** The direction pattern was uncommon in this batch, occurring in one of ten runs. That run (B09_C1) returned 25%, 25%, 25%, 25%, 24% in both rounds: six tied and four decreasing county pairs, rather than the earlier vector (two ties and eight decreases). This supports treating the earlier pattern as an observation requiring repetition, not a stable inverse-need response. It cannot identify count-omission interactions with dollar formatting or supplied estimates. Population, raw deaths, and death rates remain separate descriptors rather than one combined “need effect.”

## 5. Formalize methods, retain operational evidence, and decide the next stage

**What did we do?** Wrote `docs/methods.md`, added a saved fixed-schedule runner with durable slot assignment, and reused the existing request/retry/logging/spend machinery for ordinary and focal calls.

**Why?** The professor specifically requested reproducible retry/resume notes. Failures, duplicate runs, hidden cost gaps, or inconsistent prompts would undermine the scientific comparisons.

**How?** SDK retries remain disabled; transient failures receive at most three total attempts per logical call, with 2/4-second backoff and bounded provider delays. Only explicit, validated continuation of an empty-404 failure is supported. Source/settings/slot identity and stress parent/text must match; accepted outputs and unknown reservations are preserved. Metadata access checks are separate from response-generation attempts. No completed or arbitrary crash-interrupted run is automatically replayed.

**What results did we find?**

- Slot statuses: {'completed': 56}; campaign stop reason: none.
- Response attempts: 533; accepted outputs: 533; retries: 0; API failures: 0; parse failures: 0.
- Known input tokens: 200899; known output tokens: 34553; unknown-usage attempts: 0.
- Known new estimated cost: $0.0816434; ledger total known cost: $0.0943812; retained reservations: $0.02.
- Active run time: 910.248 seconds, excluding final report writing and between-run overhead. Per-run UTC spans and active segments are retained.
- Model-access checks: 1; explicit campaign continuations: 0.

Pricing was checked October 14 against the [official model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna) and [official pricing data](https://developers.openai.com/api/docs/pricing.md): $0.20 ordinary input, $0.02 cached reads, $0.25 cache writes, and $1.20 output per million tokens. The previous rates were unchanged; saved dated copies and `pricing_check.json` accompany this batch. Local ledger reservations are spending precautions, not known charges or remaining account credit.

**What does it mean for the project?** The requested follow-up machinery and diagnostics are implemented. **Readiness decision:** keep the star campaign deferred while reviewing the format-dependent estimate behavior and the limited communication evidence with the professor. Preserve the original baseline; the successful dollar-estimate arm is a separate information condition, not a reason to replace the baseline. Observed round-to-round movement and focal differences rule out simply describing every output as fixed in this sample, but do not establish causal neighbor influence; repeated unit/comprehension anomalies may still need attention. Star position and message volume remain linked (four messages at the center versus one at each leaf), so no centrality effect has been estimated here.

## Scope and reproduction

No new dependency, agent framework, database, dashboard, or topology campaign was added. The original baseline prompts and allocator are preserved; only the two missing format/estimate combinations were added. Source snapshots include the working code rather than relying on a Git commit that may not contain it.

Offline verification:

```bash
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python diagnostics.py --demo --phase all --demo-blocks 2
```

The live command used was `.venv/bin/python diagnostics.py --live --env-file .env --phase all`. Running it again creates a new paid campaign; it is not needed to inspect these results. The retained `verify_artifacts.py` checks the recorded arithmetic without network calls.

The later randomized-profile star experiment remains outside this completed diagnostic stage. No claim is made that the whole research project or a causal network-position analysis is complete.
