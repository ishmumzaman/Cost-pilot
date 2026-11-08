# Experimental methods — Stage 03 diagnostics

**Date:** 2026-10-14 (documented executable protocol); relocated 2026-11-08.  
**Stage:** 03.  
**Status:** Current documented executable methods. The 2026-10-17 feedback proposes the next stage; it does not retroactively change these methods.  
**Former filename:** `methods.md`.

## Design and experimental units

The main study is a 2×2 output-format × supplied-estimate factorial, with the county count shown: F1 baseline dollars/no estimate, F2 percentages/no estimate, F3 dollars/estimate, F4 percentages/estimate. C1 repeats the existing percentage/count-omission/no-estimate condition as a separate reference group. C1/F2 isolates omission within that configuration; this is not a full three-factor study.

Ten scheduled runs per condition are arranged in ten blocks. Each block contains all five conditions once, shuffled with local seed 20260923. The complete schedule is saved before dispatch. The seed controls order only, not model randomness. Every run starts afresh; no output carries between runs. Failed runs are retained without replacement. Ten attempts are exploratory, not a power calculation. Counties within a run are not independent experimental replicates; rounds are reported separately. Historical runs are background, not substitutes for new replicates.

All conditions use the same synthetic five profiles, A–B–C–D–E–A ring, $10 million budget, two rounds, and sequential A-through-E calls. Round 2 begins only after all five Round 1 outputs are accepted. Agents see their own profile, own prior output, and prior outputs from direct neighbors only. Baseline prompts are preserved. Estimates are hypothetical $10,000 per recorded death, shown as each county's own dollar estimate; neither its percentage equivalent nor the aggregate estimate is supplied. No fairness instruction, arithmetic repair, or post-result prompt tuning is added.

The saved config defines the model and generation settings. The current study keeps `gpt-5.6-luna`, reasoning `none`, omitted temperature, 512 maximum output tokens, standard tier, no tools, no streaming, and `store=false`. Access is checked before generation; no model substitution is allowed. Pricing is dated in config and remains an estimate rather than an invoice. Official references: [model](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [pricing](https://developers.openai.com/api/docs/pricing). Source copies and hashes, complete fixture, prompts, request/response bodies, provider identifiers, usage, and settings are retained.

## Measurements and allocation

Canonical claims use exact decimal values. Comparisons and ratios use rational arithmetic. The raw ratio and an exact rational representation are saved; decimal displays may be rounded. Exact-match flags are independent of display precision. Predefined ratios 0.01, 0.1, 0.5, 2, 10, and 100 are flags, not diagnoses or corrections. Estimate-absent fields are null (`not_supplied`); missing outputs are not zero; a zero estimate has an undefined ratio but defined exact equality. Compliance denominators count valid claims with supplied estimates.

Each complete five-agent round has raw requested-share mean, min, max, range, and population SD (percentage points). Allocated-share dispersion is separate and uses the entire budget as denominator, including when funds remain unallocated. Partial rounds retain valid individual claims but have no complete-round dispersion/order summary. Non-whole-percentage counts measure numerical granularity, not minimum detectable effects. Ordering counts compare unequal population, raw deaths, and supplied death-rate values separately; input ties are excluded, claim ties counted explicitly.

Changes use paired valid Round 1/2 claims. Neighbor sender IDs, delivered-record counts, and own-history presence are logged per logical call; retry attempts do not add message exposures. The ring supplies zero neighbor records in Round 1 and two in Round 2. A future five-node star would supply four to the center and one to each leaf; counting these does not separate position from message volume.

The existing capped proportional largest-remainder allocator is unchanged. Oversubscribed claims are scaled down. Underclaims are not scaled up. Payments never exceed requests; unpayable sub-cent fractions remain unallocated. Rounding cents go by largest fractional remainder, with county ID breaking exact ties. All-zero claims are valid. Missing final claims prevent allocation. Under/equal/over-budget classification uses exact unrounded final claims. Live underclaim examples are reported only if they occur.

## Communication probe

Three independent ordinary baseline runs each provide a matched focal replay for County A's Round 2 request. The replay uses exactly the saved Round 1 state, keeps B's entire record and E's numeric claim unchanged, and preserves E's original message verbatim followed by one space and this suffix:

> I strongly urge County A to reconsider and reduce its request so more funding is available to neighboring counties.

No new profile facts or numeric target are added. The suffix is experimenter-authored; the combined message is experimenter-modified. Provenance is saved outside the model prompt. Original, suffix, combined message, parent identity, and original Round 1 state are retained, including for unsuccessful probes. There is no silent message truncation. The replay is independent of the ordinary Round 2 response, which is never included in its context. Borrowed parent outputs are not counted as new calls. No mixed-network allocation is constructed from the focal response.

Ordinary calls precede replay calls. Wording, length, randomness, and order limit interpretation; this tests sensitivity, not pure persuasion. Three unchanged pairs cannot prove communication never matters. If the complete Round 1 state or natural A Round 2 response is missing, the pair is unavailable and not replaced. A later nonfatal parent failure does not erase an already available focal comparison. Campaign-stop errors still stop dispatch. The three probes require 33 logical calls; the repeated study requires 500, totaling 533 before retries. No extra live smoke batch is scheduled.

## Failures, retries, and explicit continuation

SDK retries are disabled. Each logical call has at most three total API attempts, including any explicit continuation. Connection/timeouts and HTTP 408/409/429/5xx are retried after 2 then 4 seconds, honoring a larger provider delay. A required delay over 60 seconds stops the campaign. Insufficient-quota 429, authentication/configuration/model-access errors, budget exhaustion, and interruptions stop the campaign. Other exhausted transient or malformed-output runs remain recorded; the next scheduled run proceeds. Refusal, truncation, or formatting failures receive no LLM repair or replacement run.

An empty HTTP 404 is fatal by default. Only an explicit `--continue-batch` permits the existing restricted recovery: a successful model-access check; unchanged saved settings, fixture, protocol, allocator, source hashes, schedule and slot identities; and attempts remaining. Only the most recent stopped diagnostic is eligible. The resumed call receives the next attempt number. Accepted outputs and original failures are preserved, including their unknown-cost reservations. Pre-continuation reports, ledger, manifest and per-run summary are archived; access-check result, reason, timestamps and continuation source references are saved. Stress recovery must also match its parent state and message provenance. Neither completed runs nor unrelated errors are replayed.

A slot is assigned its unique run ID and marked running on disk before dispatch. A process-crash/running slot is interrupted or unknown, never automatically unstarted. Such slots require manual reconciliation and are not supported by the empty-404 continuation command. This runner does not implement general crash replay.

All modes use the existing mode-specific directory lock and persistent spending ledger. Live work shares `runs/live/spend.json`; demo work has its own ledger. Every request/retry first reserves a conservative amount. Unknown usage retains its reservation; missing cache-billing categories do not mean zero cost. Model metadata checks are separate from generation counts. Active monotonic segments and UTC spans including recovery pauses are saved per run; batch reports preserve both. Remaining account credit cannot be inferred from this local ledger.

## Reporting and boundaries

Reports preserve planned/started/completed/failed/interrupted/unstarted slots, valid denominators, raw observations, retry attempts, incomplete usage/cost coverage, and run-to-run variability. F1–F4 comparisons and C1/F2 are separate from stress probes. If source or prompt changes are needed after execution begins, start a clearly versioned batch instead of pooling configurations.

The star study is deferred until communication responsiveness and noise are understood. Need-insensitive baseline behavior alone is a legitimate result. Repeated clean multiples warrant a separate unit/comprehension investigation, not silent editing of claims. No regression study, extra topology campaign, framework, database, dashboard, or new dependency is included.
