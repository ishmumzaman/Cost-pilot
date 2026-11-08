# Stage 03 — Need and communication implementation plan

**Date:** 2026-09-23 (prepared); executed 2026-10-14.  
**Stage:** 03 / Update 3.  
**Former filename:** `need_and_communication_implementation.md`.

**Prepared:** September 23, 2026.  
**Source:** Professor Wayne's September 17, 10:33 PM reply supplied in the latest email exchange.  
**Status (October 14, 2026):** Implemented and executed. All 50 repeated runs and three paired communication probes completed (533 successful calls). All 59 tests and the independent artifact audit passed. See [Update 3](../reports/2026-10-14-stage-03-format-communication.md) for results and the [methods](../methods.md) for execution rules. The star study remains deferred.

The sections below preserve the agreed design and implementation checklist; references to planned changes describe the work now completed.

**Scope:** Four factorial conditions plus one count-omission reference group, ten scheduled runs each; three matched communication probes. This revision reduces the repeated experiment from 80 to 50 runs while retaining coverage of the professor's feedback.

## 1. Objective and actionable items

Determine whether claims use supplied funding estimates, whether neighbor messages can influence claims, and whether the earlier patterns persist under controlled repetition. Preserve the original baseline as a legitimate experimental condition. Need-insensitive baseline behavior is not, by itself, an engineering defect.

| ID | Action from the feedback | Concrete deliverable |
|---|---|---|
| A1 | Log claim relative to the supplied estimate | Per-agent, per-round claim/estimate ratio; exact-match flag; counts of predefined simple multiples |
| A2 | Observe underclaim behavior if it occurs naturally | Raw total claims, allocation total, unallocated amount, and under/equal/over-budget classification |
| A3 | Test whether communication can move a claim | A small, matched ordinary-message versus forceful-message stress test |
| A4 | Track compression of claims directly | Per-round range and standard deviation of requested budget percentages, with allocation dispersion separately |
| A5 | Preserve the baseline and separate added information | Original baseline retained; local estimates remain an information-intervention arm |
| A6 | Repeat with a percentage-only control and factorial design | Four-cell format × estimate factorial; ten scheduled runs per cell; retain all failures |
| A7 | Recheck the ordering pattern without overstating need | Ten additional count-omission reference runs; separate comparisons with population, raw deaths, and death rate |
| A8 | Record received messages per agent | Neighbor sender IDs and delivered-message count per logical call, distinct from own prior output and API retries |
| A9 | Formalize retry and continuation methods | A short `docs/methods.md` describing automatic retries, the restricted empty-404 continuation, failure retention, and accounting |
| A10 | Defer position-effect claims until the protocol is understood | Report a readiness decision for a later randomized-profile star study; acknowledge position/message-count confounding |

Completion means these measurements, fixed experiments, and an honest results report exist. It does not require agents to comply, change claims, spend the entire budget, or produce an interesting scientific result.

## 2. Existing implementation to reuse

The current code was inspected for this plan:

- [pilot.py](../../pilot.py) already provides exact numeric parsing, unit conversion, neighbor-only prompts, the Round 1 barrier, the corrected allocator, attempt logging, a persistent spending guard, and source/timing snapshots. `diagnostics()` already records claim totals and changes, but not the requested estimate ratios, dispersion, or explicit message counts.
- `PROTOCOLS` currently contains `baseline` (dollars, count shown, no estimate), `local_need` (percentages, count shown, estimate), and `hidden_count` (percentages, count omitted, no estimate).
- [followup.py](../../followup.py) has a fixed two-run schedule, descriptive death-order comparisons, and the explicit empty-404 continuation workflow. Retain it as the runnable Update 2 procedure rather than silently changing its meaning.
- [tests/test_pilot.py](../../tests/test_pilot.py) and [tests/test_update2.py](../../tests/test_update2.py) cover parsing, allocation, failures, accounting, and continuation. Run them during implementation; this planning pass did not rerun tests.
- [Stage 02 report](../reports/2026-09-17-stage-02-follow-up-diagnostics.md) documents the previous diagnostics. Its claims, failures, and allocations are historical observations; do not rewrite them into the new experiment.

Reuse the two installed dependencies. Add no agent framework, database, dashboard, or general experiment-management system. Keep the approved allocator unchanged.

## 3. Freeze the repeated experiment before running it

### Main factorial: 2 × 2, plus one reference group

The professor requested a small factorial and roughly ten runs per cell, but did not specify its exact factors. Use output format × local estimate as the main factorial, with the county count shown in all four cells. This separates format from supplied information without testing every combination of three factors.

| Cell | Output format | County count | Local estimate | Relationship to current code |
|---|---|---|---|---|
| F1 | Dollars | Shown | Absent | Existing `baseline`; preserve its rendered prompts |
| F2 | Percentages | Shown | Absent | New percentage-only control; otherwise identical to F1 |
| F3 | Dollars | Shown | Present | New; isolates estimate effects against F1 |
| F4 | Percentages | Shown | Present | Existing `local_need` |
| C1 — reference | Percentages | Omitted | Absent | Existing `hidden_count`; outside the four-cell factorial |

Keep C1 because the professor also said the decreasing-claim ordering in the count-omission run deserves another look. Repeating that condition and comparing it with F2 covers this concern without adding a full county-count factor. C1 tests count omission only with percentage output and no estimate; it does not identify interactions with format or estimates.

Schedule **10 runs per condition: 40 factorial runs plus 10 reference runs, totaling 50 runs and 500 logical agent calls** before retries. These are scheduled run slots, not a guarantee of ten successful runs; failed runs are retained without replacement. Ten is an initial descriptive sample, not a power calculation. Historical one-off runs are background evidence, not replacements for these new replicates.

Use ten blocks, each containing F1–F4 and C1 once. Shuffle condition order within each block using a saved local scheduling seed (default `20260923`) and save the complete schedule before the first paid call. This reduces systematic time/order confounding. The seed controls scheduling only; it does not make model responses reproducible. Each run starts independently with no conversation state carried between runs; block membership is a scheduling device, not a matched model-randomness seed.

Fixed across conditions:

- Five existing profiles in [counties.json](../../counties.json), the A–B–C–D–E–A ring, two rounds, the $10 million budget, and A-through-E call order within each round. No profile reassignment in this stage.
- Current provider/model and generation settings from [config.json](../../config.json). This is reuse of the existing configuration, not a new model recommendation. Recheck access and dated pricing before execution; never silently switch models.
- Current advocacy instructions, permitted context, response validation, retry policy, and `capped_proportional_largest_remainder_v2` allocator.
- In estimate-present cells, the same hypothetical $10,000 per recorded death, supplied only as the county's own dollar estimate. Do not add its percentage equivalent only to some cells: that would introduce another factor.
- No fairness instruction, instruction to copy the estimate, arithmetic repair, forced decimal precision, or prompt tuning after results appear.

Changing a factor must alter only the corresponding prompt fields. A percentage-only control may change output-unit instructions and the units of prior-message claim fields; it must not gain additional examples, reasoning instructions, or information. Treat possible inference of the county count from labels/messages as a limitation of omission, not proof of successful concealment.

Primary comparisons: F2 versus F1 for output format without added estimates; F3 versus F1 and F4 versus F2 for local estimates at fixed format/count; F4 versus F3 for output format with estimates. Compare the estimate contrasts descriptively to assess whether the estimate response differs by format. Report C1 versus F2 separately for count omission with percentage output and no estimate, alongside whether C1's original ordering pattern repeats. Report per-condition results and these controlled comparisons rather than pooling all conditions into one scientific average. No full three-factor analysis is planned.

## 4. Add the measurements

Keep raw responses unchanged. Compute derived metrics from exact canonical claim amounts, before allocator rounding. Log by agent and round, with cell, block, run, and logical-call identifiers.

### Claim/estimate behavior — A1 and A5

For estimate-present cells, save `supplied_estimate_usd`, `claim_to_estimate_ratio`, and `claim_equals_estimate`. The ratio is the raw requested amount divided by the supplied estimate; equality uses exact decimal/rational comparison, not displayed rounded values.

Also flag exact ratios in the predefined set `{0.01, 0.1, 0.5, 2, 10, 100}`. Report the raw ratios alongside these counts; the set is a diagnostic default, not an exhaustive definition of arithmetic error. Ratio 1 is reported separately as exact compliance. Do not invent a post hoc tolerance or automatically correct clean multiples.

When no estimate was supplied, all estimate-related fields are null with reason `not_supplied`; do not calculate a hypothetical estimate and call it compliance. If an explicitly supplied estimate is zero, the ratio is null with reason `zero_estimate`, but exact equality remains defined: a zero claim matches, a positive claim does not. Failed/missing outputs remain missing, never zero. Compliance denominators count valid responses with supplied estimates; report missing outputs separately.

### Dispersion, precision, and ordering — A4 and A7

For each complete five-agent round, derive requested budget percentages and report their mean, minimum, maximum, range, and **population standard deviation** across the five agents. Range and SD are in percentage points. Compute a separate SD/range for final allocated budget percentages; do not confuse normalized allocations with raw claims or renormalize away unallocated funds.

Record the count of non-whole-percentage claims among valid outputs. Decimal percentages are evidence of numerical granularity, not a measured minimum detectable effect. Calculate comparisons using full precision, then round only presentation values.

Extend the existing pair-order diagnostic separately for population, raw death count, and death rate. Among pairs with unequal values of the chosen input, count increasing, equal, and decreasing claims and save the denominator. Do not pool these into a single “need effect.” Inputs tied on the chosen indicator are excluded from its ordered-pair denominator. Constant claims can be reported as nonincreasing, but must be distinguished from strictly decreasing claims through the tie count.

Complete-round dispersion/order summaries are null if any claim is missing; retain individual valid claims and observed counts. Across cells, summarize run-level measurements, not a pooled set of counties presented as independent replicates. Keep rounds separate.

### Communication and underclaiming — A2, A3, and A8

- Preserve existing raw claim changes; add change in budget percentage points and an exact changed/unchanged flag for agents with both rounds available. Report paired count, unchanged count, and mean absolute change per run. One changed output alone is not proof of a message effect.
- Log `neighbor_message_count`, `neighbor_sender_ids`, and whether an own-prior-output record was supplied. In the normal ring, counts are 0 in Round 1 and 2 in Round 2; own prior output is not a neighbor message. Retries repeat a logical call and do not create additional experimental messages. Count records actually delivered, not entities merely mentioned in prose.
- Derive under/equal/over-budget classification from the exact total of five valid final claims. Save unallocated cents and the allocated-plus-unallocated conservation check. Preserve the all-zero valid case. Missing final claims make this classification unavailable.
- In a live underclaim example, show raw requests, actual payments, and retained surplus. If none occurs, state that plainly. Do not force compliance, lower estimates after inspecting results, or substitute a simulated example for live evidence.

## 5. Run a small matched communication stress test

Use a **forceful-message test**, one of the two alternatives the professor suggested. Do not also add extreme-profile experiments in this stage. Default scope: three predeclared matched diagnostic pairs, using the unchanged dollar-output baseline.

For each pair:

1. Run a normal five-agent/two-round baseline once and retain all artifacts.
2. Take County A's exact saved Round 1 state and neighbor records. Construct an alternative Round 2 request for A from that same state; do not use any Round 2 output as its context.
3. Preserve neighbor E's original message verbatim and append only the fixed advocacy text below, separated by one space. Keep E's numeric claim, B's entire record, A's own prior output/profile, budget, and prompt instructions unchanged. The alternative call remains an independent request, not a continuation of the natural Round 2 conversation.
4. Freeze this appended text before any stress calls: “I strongly urge County A to reconsider and reduce its request so more funding is available to neighboring counties.” Do not insert E's full profile, additional factual claims, an invented emergency, or a prescribed claim amount. Do not rewrite, truncate, or use another model to strengthen the original message. Label the experimental override in saved artifacts, without adding a provenance notice to the model's prompt; any ordinary message-length validator must not silently trim it.
5. Save the original message, exact suffix, and combined message. Mark the suffix as `experimenter_authored` and the combined message as `experimenter_modified`, while identifying its sender as E in the experimental packet. The combined message must never be represented in the dataset as wholly model-generated.
6. Compare A's ordinary Round 2 claim, stress Round 2 claim, and shared Round 1 claim. Save signed and absolute differences in percentage points. Do not create a second full-network allocation by mixing the stress response with other agents' ordinary responses.

This is **33 logical calls** if all three normal runs and three extra focal calls complete. The natural response is always collected first; log that order and acknowledge stochastic/order effects. Appending advocacy changes wording and length, so this is a communication-sensitivity probe, not a pure estimate of persuasion or a causal-effect estimate. Three pairs cannot establish that communication never matters. A stronger attribution test could later include repeated identical-prompt controls, but is not a prerequisite here.

An incomplete Round 1 or missing natural A Round 2 output makes the pair unavailable; record it without replacement. A failure later in the natural round does not erase an already valid focal pair, but the parent run remains incomplete. Use the same API logging, parser, retry policy, and shared spending guard for the extra call. Stress calls belong to a separate dataset and never count as factorial replicates.

If stress and ordinary claims remain unchanged, report that and continue the fixed repeated experiment to examine variation across conditions; do not tune messages until they work. Pause the later star study while communication responsiveness remains unresolved. If a difference appears, it shows possible responsiveness under this probe, not stable influence or a centrality effect.

## 6. Minimal code and artifact changes

| File | Planned change |
|---|---|
| `pilot.py` | Add only two missing protocols: percentage-only control and dollar-output local estimate. Preserve the three existing prompt variants. Extend diagnostics/message provenance. Extract the existing per-agent request/retry/logging operation into one helper so the stress call uses the same machinery. Keep the allocator unchanged. |
| `diagnostics_config.json` — new | Four factorial cells plus C1, ten scheduled runs each, scheduling seed, three stress pairs, frozen advocacy suffix, and diagnostic factor flags. Keep experimental scheduling settings outside the strict provider-config schema. |
| `diagnostics.py` — new | Thin runner for the frozen repeated experiment and separate stress phase; use `pilot.py` for calls and computation. Label each condition as factorial or reference, and separate operational totals from per-condition scientific results. |
| `docs/methods.md` — new | Fixed design, experimental units, context/message provenance, retry/continuation rule, failure accounting, and limits. |
| `tests/test_diagnostics.py` — new | Targeted checks for controls, new metrics, schedules, stress isolation, and continuation identity. Keep existing suites. |
| `README.md` | Document the new entry point and artifact paths after implementation. |
| `docs/reports/2026-10-14-stage-03-format-communication.md` — produced after execution | What/why/how/results/meaning for measurement changes, stress test, factorial, count-omission reference, and methods; include a readiness decision. |

Proposed CLI contract, **not yet implemented**: `diagnostics.py --demo --phase all` and `diagnostics.py --live --env-file .env --phase stress|repeated|all`, with explicit continuation of an existing batch rather than an ambiguous automatic restart. The `repeated` phase includes F1–F4 and C1 in the same saved schedule.

Store new manifests, source snapshots, original requests/responses, metrics, and reports under a unique `runs/live/update3_*/` batch, with referenced individual run directories. Continue using the existing `runs/live/.lock` and `runs/live/spend.json`; do not create an independent ledger that forgets prior spend. Demo artifacts remain under `runs/demo/`.

A manifest must record all planned slots, factor settings, schedule order/seed, source hashes, fixture and prompt definitions, allocator version, and outcomes including unstarted slots. A run ID may occupy only one scheduled slot. Persist slot assignment before dispatch and progress after each run. Do not label a process-crash slot as unstarted or automatically rerun it: retain an explicit interrupted/unknown state for reconciliation. Existing source snapshots and per-call logs should be reused rather than replaced by another logging system.

## 7. Methods: retry and saved-state continuation

Document the policy already implemented, then adapt only the identities needed by the new runner:

- SDK retries remain disabled. At most three total API attempts per logical call, including any explicit continuation attempt. Transient connection/timeout errors and HTTP 408/409/429/5xx follow the current retry loop: waits of 2 then 4 seconds, honoring a larger provider delay. If the required delay exceeds the configured 60-second maximum, stop and record it.
- Authentication/configuration/model-access errors, insufficient quota, budget exhaustion, and interruptions stop the campaign for review. Other exhausted transient or malformed-output runs remain recorded failures; continue subsequent scheduled slots when no campaign-stop condition applies. Formatting errors, refusals, and truncation receive no LLM repair or replacement run.
- An empty HTTP 404 is not automatically transient. The existing special path permits explicit continuation only after a successful model-access check, matching saved inputs/prompts/settings/allocator, and with attempts remaining. Preserve accepted outputs, append the failed logical call's next attempt, retain the original failure, and archive pre-continuation summaries and source.
- The current code limits this path to `kind="diagnostic"`. Retain that kind for the new protocol diagnostics, and additionally validate batch/condition/block/slot identity. For a stress continuation, also match the parent Round 1 state, original message, appended suffix, combined message, and provenance. Never resume into another condition or arm.
- Save the access-check outcome, reason, attempt IDs, continuation time, and source references. Save both active execution segments and total UTC span including pauses. A successful resumed run still reports its failed attempt and incomplete cost coverage if usage is missing.
- Reserve estimated spend before every request/retry. Unknown usage retains its reservation and is not treated as free. Provider-metadata access checks are separate from response-generation counts. Document manual recovery separately from automatic backoff.

Do not expand this into arbitrary crash replay or automatic continuation after unrelated errors. A complete run must never be silently re-executed to improve its outcome.

## 8. Implementation order and verification

1. **Freeze the design and methods.** Add the experiment configuration and draft `docs/methods.md`, including exact cell definitions, stress text, scheduling/failure rules, and the distinction between requested requirements and chosen defaults.
2. **Implement metrics and controls.** Extend the protocol dictionary and diagnostics. Compare rendered F1, F4, and C1 prompts with their existing equivalents; compare F1/F2 prompts to ensure the control changes output units only. Check F1/F3 and F2/F4 differ only in estimate provision, F3/F4 only in output units, and F2/C1 only in the count statement for equivalent supplied history. Preserve source and raw-output provenance.
3. **Build the thin runner and stress call.** Share existing call/error/spend machinery. Persist the schedule and slot identities, and ensure factorial/reference/stress/development results remain distinguishable. Do not let `config.json`'s old `measured_runs=5` silently schedule extra runs.
4. **Validate offline before spending.** Run existing suites and the new deterministic demo, including a shortened two-block schedule with all five conditions in each block. Demo results are never research evidence.
5. **Execute the fixed stress phase, then repeated experiment.** Keep the model/settings/prompts fixed. Unexpected behavior is data, not a reason to replace runs. Stop for implementation/access/spending faults; preserve and disclose any incomplete campaign. An implementation fix that changes prompts or measurements starts a clearly versioned batch instead of silently pooling configurations.
6. **Audit and report.** Independently reconcile numeric conversions, estimate ratios, messages delivered, allocations, attempt counts, and ledger totals. Generate the report from saved artifacts without additional model calls.

Required new offline checks:

- Ratios and equality: 1×, 2×, 10×, non-round ratios, absent/zero estimates, tiny deviations, equivalent dollar/percentage claims, and missing outputs. Metric labels must not diagnose an arithmetic error automatically.
- Dispersion: constant claims give range/SD zero; known unequal vectors match an independent calculation; partial rounds stay tagged incomplete; precision counts are calculated before rounding.
- Communication: correct sender counts per round, own-history exclusion, retries not double-counted, and an illustrative star adjacency fixture yields four center messages versus one leaf message. This fixture is a logging test, not a new topology experiment.
- Repeated experiment: exactly four factorial cells plus one separately labeled reference group and ten slots per condition; reproducible schedule with all five conditions per block; no extra baseline smoke run, replacement of failures, or duplicate completed slot after continuation.
- Stress: E's original message is preserved verbatim with only the frozen suffix appended; no additional profile facts or numeric claim changes; other context remains identical; natural/stress responses share the saved Round 1 parent; malformed stress results remain missing; no fabricated full-network stress allocation.
- Methods/accounting: append-only attempt records, bounded continuation, settings/cell/provenance mismatch rejected before dispatch, prior unknown reservations retained, active versus paused timing distinguished, and no full-cost projection with incomplete usage.

## 9. Reporting, cost, and readiness

The plan schedules **40 factorial runs plus 10 count-omission reference runs, three normal stress-parent runs, and three additional focal calls: 533 logical calls** (400 + 100 + 30 + 3), excluding retries and separately labeled development work. Do not add a live smoke batch automatically; use offline validation and retain the first scheduled live outcome as its scheduled outcome.

The September 9 measured mean was about $0.00156 per ten-call run. Using that historical usage as a rough yardstick gives about **$0.08** for the planned calls. Added context, retries, pricing changes, and unknown usage can change this amount; this is not a verified current quote or complete billing forecast. Recheck pricing at execution and keep the existing $1 local guard. At the original planning inspection the ledger held $0.0127378 known estimated cost plus $0.02 in unresolved reservations; preserve those reservations and check the current ledger before execution. Do not infer the account's remaining credit from this ledger.

The results report must include:

- Planned/started/completed/failed/interrupted/unstarted run slots for each condition and stress pair; API failures, retries, explicit continuations, parse failures, token totals, active/UTC timing, known cost, and missing-cost coverage.
- Per-agent raw claims in comparable budget percentages, supplied-estimate ratios and exact compliance where applicable, and counts of predefined simple multiples, separately by round and cell.
- Run-level claim dispersion, output granularity, population/death-count/death-rate ordering, and claim changes. Include valid denominators; do not treat 50 county outputs in a cell as 50 independent runs.
- Underclaim frequency, unallocated amounts, and an audited live example if one occurs. State explicitly if only offline tests have exercised that path.
- Natural-versus-stress focal results with the original message, authored suffix, combined message, and provenance. Distinguish “unchanged,” “changed,” “missing,” and “insufficient evidence of influence.”
- Factorial contrasts with observed run-to-run variability, plus the separate C1/F2 comparison and count-omission ordering replication. Ten scheduled runs per condition are exploratory; no minimum detectable effect, statistical-power claim, or network-position coefficient is warranted from this design alone. Do not present C1 as a complete third factorial dimension.

**Decision for the next stage:** If valid claims remain unresponsive even under the stress probe and across repeated conditions, investigate the communication protocol before collecting star-position results. If responsiveness appears, assess its consistency and noise before advancing. Need-insensitive baseline behavior alone is not a stop condition: the contrast with an information arm may be the result of interest. Repeated clean-multiple anomalies warrant a separate unit/comprehension diagnostic, not silent claim correction.

The eventual five-node star requires randomized profile assignment across structurally distinct positions. Its center receives four neighbor messages and each leaf one. Message counts document that joint change but do not, by themselves, identify a centrality effect independent of message volume; a separate design would be needed to distinguish those mechanisms. No star campaign, real-data table work, new literature search, or regression study is included in this implementation stage.

## 10. Done checklist

- [x] A1–A10 have either an implemented deliverable or an explicit next-stage boundary.
- [x] Original baseline prompts and historical artifacts are preserved; four factorial cells and the separate count-omission reference group are controlled and documented.
- [x] Metrics cover estimate ratios/compliance, dispersion, ordering, message exposure, claim change, and surplus with correct missing-data handling.
- [x] The communication probe preserves the shared state and original message, appends only the frozen advocacy text, and records its authorship.
- [x] Offline verification passes; the live schedule is frozen and all started attempts are retained.
- [x] Retry/continuation methods match the actual implementation and preserve shared spend accounting.
- [x] `docs/reports/2026-10-14-stage-03-format-communication.md` answers what was done, why, how, results, and project implications for each workstream, including a candid star-readiness decision.

A flat, noncompliant, underclaim-free, or partially failed result can satisfy this checklist if the evidence and limitations are accurately recorded. Desired scientific outcomes are not acceptance tests.
