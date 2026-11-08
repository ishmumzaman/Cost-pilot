# Stage 02 (Update 2) — Follow-up diagnostics

**Date:** 2026-09-17 (implementation and testing).  
**Stage:** 02 / Update 2.  
**Status:** Completed historical report addressing the 2026-09-09 feedback.  
**Former filename:** `update2.md`.

**Implemented and tested:** September 17, 2026.  
**Scope:** The two requested five-agent/two-round prompt diagnostics, percentage-resolution inspection, and the allocator correction. Each item below answers: what, why, how, results, and meaning for the project.

**Main finding:** The local funding estimate changed the pattern and precision of claims, but did not make every county's claim track its estimate. Omitting the county count did not produce a positive relationship between claims and deaths in this run. The allocator changes are implemented and tested. These are two small diagnostic runs, not evidence that the research hypothesis or the need-response problem has been resolved.

**Evidence:** [Live results](../../runs/live/update2_20260917T211359_3d3f870d/results.md), [full results and summaries](../../runs/live/update2_20260917T211359_3d3f870d/results.json), [predeclared schedule/settings](../../runs/live/update2_20260917T211359_3d3f870d/manifest.json), [live artifact verification](../../runs/live/update2_20260917T211359_3d3f870d/verification.json), [offline test output](../../runs/live/update2_20260917T211359_3d3f870d/offline_tests.log), and [deterministic allocator examples](../../runs/live/update2_20260917T211359_3d3f870d/allocator_checks.json). The [original September 9 baseline](../../runs/live/batch_20260909T043530_41863619/report.md) remains unchanged.

## 1. Test a local funding estimate as an alternative reference point

### What did we do?

Ran the same five synthetic counties through two discussion rounds with an added estimate of what fully funding each county would cost. This variant is named `local_need`. It retained the explicit five-county count and requested claims as percentages of the total budget.

### Why did we do it?

The professor observed that claims clustered around the $2 million equal split, despite large differences in need. Providing an own-county funding estimate gives agents a concrete reference besides budget divided by five. This tests whether claims can respond to a need-linked numeric input at all.

### How did we do it?

Before calling the API, fixed a common **hypothetical $10,000 per recorded overdose death** multiplier. Each agent saw only its own resulting estimate, alongside its existing profile. This is a synthetic planning assumption, not an empirical intervention cost, a cost per death prevented, or a public-health recommendation. It is a diagnostic proxy based on recorded deaths, not a complete definition of need.

The estimates are deliberately not normalized to exhaust the budget. Together they total $8.57 million, or 85.7% of the $10 million budget; that global total was not shown to agents. We did not change the multiplier after seeing responses or instruct agents to copy their estimate.

| County | Synthetic deaths | Own funding estimate | Estimate as % of budget |
|---|---:|---:|---:|
| A | 24 | $240,000 | 2.4% |
| B | 61 | $610,000 | 6.1% |
| C | 92 | $920,000 | 9.2% |
| D | 205 | $2,050,000 | 20.5% |
| E | 475 | $4,750,000 | 47.5% |

For example, County A's prompt added a hypothetical $240,000 estimate, calculated as $10,000 times its 24 deaths. The prompt explicitly labeled the estimate synthetic. No other county's profile or funding estimate was included directly, though neighbors could disclose information in their messages.

The API model and settings remained `gpt-5.6-luna`, reasoning `none`, omitted temperature, 512 maximum output tokens, standard service tier, sequential calls, and the A–B–C–D–E–A ring. No fairness objective was added. The protocol was frozen before its first call. See the [saved configuration](../../runs/live/20260917T211359_diagnostic_814571e70a/config.json) and [full attempt log](../../runs/live/20260917T211359_diagnostic_814571e70a/calls.jsonl).

### What results did we find?

| County | Round 1 requested % | Round 2 requested % | Final claim / local estimate | Final allocation as % of budget |
|---|---:|---:|---:|---:|
| A | 24% | 24% | 10× | 21.1640212% |
| B | 12.2% | 12.2% | 2.0× | 10.7583774% |
| C | 9.2% | 9.2% | 1.0× | 8.1128748% |
| D | 20.5% | 20.5% | 1.0× | 18.0776014% |
| E | 47.5% | 47.5% | 1.0× | 41.8871252% |

- **C, D, and E matched their estimates exactly.** Their final claims were 9.2%, 20.5%, and 47.5%.
- **A requested ten times its estimate:** 24% of the budget ($2.4 million), compared with an estimate of 2.4% ($240,000).
- **B requested twice its estimate:** 12.2% ($1.22 million), compared with an estimate of 6.1% ($610,000).
- No county changed its numeric claim between rounds. Total claims stayed at **113.4%** of the budget, a **13.4% overshoot**. The final proportional allocator spent 100%, leaving no surplus in this run.

The A and B percentages agree with the dollar amounts they stated in their messages. The discrepancy with their estimates is therefore in the model's requested amounts, not the software's percentage-to-dollar conversion. We cannot tell from these outputs whether this reflects advocacy, numerical anchoring, arithmetic confusion, or another cause; the outputs were retained as given.

As a simple descriptive ordering check, **6 of the 10 distinct county pairs** had higher claims in the county with more deaths; 4 had the opposite order and none tied. The counts are the same in both rounds. This check does not account for mortality rate, vulnerability, poverty, or population, and the pairs are not independent experimental observations.

### What does it mean for our project?

The model can use an explicit local estimate: three counties matched it, and the overall claims were more spread out than the original near-equal-split pattern. But **we have not fixed need sensitivity consistently**. County A's large over-request is particularly important to retain and discuss.

This is promising evidence for testing explicit local estimates further, not a reason to declare this the validated baseline. Deaths are only one component of need, and copying a supplied estimate is not evidence of independent public-health reasoning. One run per variant is too small to establish stability or estimate need coefficients.

## 2. Test omitting the number of counties

### What did we do?

Ran a second five-agent/two-round diagnostic named `hidden_count`. It provided the $10 million budget but omitted the sentence stating that five counties share it. It did not add a local funding estimate and also requested percentage claims.

### Why did we do it?

Removing the explicitly supplied divisor tests the professor's concern that agents were anchoring on budget divided by county count. It is a small prompt change intended to reduce that direct equal-split reference.

### How did we do it?

Kept the original profiles, graph, call order, model/settings, two-round barrier, and neighbor-only message access. Removed only the explicit count line from the baseline's context, alongside the percentage-output change shared by both diagnostics. Round 2 passed each agent its own and its two neighbors' Round 1 percentages/messages.

This omits the explicit count; it does **not guarantee ignorance of the count**. Anonymous labels A–E and neighbor identities can offer clues, and model-generated messages may make assumptions. We did not relabel or shuffle counties in this diagnostic because that would introduce further changes.

### What results did we find?

| County | Deaths | Round 1 requested % | Round 2 requested % | Final allocation as % of budget |
|---|---:|---:|---:|---:|
| A | 24 | 28% | 28% | 21.875% |
| B | 61 | 28% | 28% | 21.875% |
| C | 92 | 25% | 25% | 19.53125% |
| D | 205 | 25% | 25% | 19.53125% |
| E | 475 | 22% | 22% | 17.1875% |

All claims were unchanged in Round 2. The total was **128% of the budget**, a **28% overshoot**, compared with the original baseline's mean totals of 113% in Round 1 and 108.2% in Round 2. These are descriptive comparisons across different dates and prompt formats, not estimated treatment effects.

County E, with 475 deaths, requested **22%**, the smallest share. Counties A and B requested **28%** each. Among the 10 county pairs ordered by deaths, **0 were concordant, 2 tied, and 8 were discordant**. The final allocator normalized claims to the budget, with no surplus. See the [run summary](../../runs/live/20260917T211804_diagnostic_4375845f1a/summary.json) and [raw messages](../../runs/live/20260917T211804_diagnostic_4375845f1a/calls.jsonl).

### What does it mean for our project?

Omitting the count **did not solve death-linked claim responsiveness in this observed run**. It also did not reduce overshoot. This does not prove that count omission always fails or that a claim must be proportional to deaths; county profiles contain other need indicators. It does mean we should not adopt count omission as a demonstrated fix based on this test.

The two diagnostics differ in both the presence of a local estimate and the explicit count. Both also differ in output format from the historical baseline. Without a contemporaneous percentage-only control and repeated runs, we cannot isolate the separate causal effects of these prompt changes.

## 3. Check the numerical resolution of percentage claims

### What did we do?

Used percentage outputs in both diagnostic runs and checked whether claims extended beyond whole percentage points. Converted the old dollar claims to percentages for comparison, without modifying the old artifacts.

### Why did we do it?

In a $10 million budget, $100,000 equals **one percentage point**. The original claims all lay on that grid. A smaller effect might be hard to observe if outputs remain that coarse. The professor asked whether expressing requests as percentage shares would produce finer answers.

### How did we do it?

Changed the required output field to `claim_percent`, with 100 explicitly defined as the whole budget, and retained the brief message. No example percentage, required number of decimal places, or minimum increment was supplied. Responses were parsed as exact decimals, the original percentage was saved, and dollars were derived as `budget × claim_percent / 100`. Neighbor prompts carried percentages rather than converted dollar fields.

The parser rejects numeric strings, percent-sign strings, booleans, negative/nonfinite numbers, duplicate keys, extra fields, and malformed JSON. It accepts finite nonnegative claims above 100% rather than silently clipping overclaims. Raw messages may still mention dollars; the numeric claim field is the percentage used by the software.

### What results did we find?

| Response population | Non-whole-percentage claims | Observed values/examples |
|---|---:|---|
| Original five measured runs, both rounds | 0 / 50 | All values were whole percentage points |
| Local-estimate diagnostic, both rounds | 8 / 10 | 12.2%, 9.2%, 20.5%, 47.5%, repeated in Round 2 |
| Count-omission diagnostic, both rounds | 0 / 10 | 28%, 28%, 25%, 25%, 22%, repeated in Round 2 |

All **20 successful new responses parsed correctly**, with no formatting repair or parse retry. The local-estimate outputs used tenths of a percentage point, equivalent to $10,000 increments for this budget. The count-omission outputs stayed at whole percentage points.

### What does it mean for our project?

The output and parsing pipeline can represent finer claims, and the model produced them when local estimates were present. **Percentage wording alone is not shown to solve coarse rounding.** The local estimates themselves contained values corresponding to tenths of a percentage point, so copying or using that precision is an alternative explanation.

Observed decimal places are not a measured minimum detectable effect, and two runs cannot determine how many replicates the final study needs. Replicate planning still requires repeated observations under a settled prompt and an estimate of between-run variation. We preserved the finer outputs without treating them as evidence of greater substantive accuracy.

## 4. Correct underclaim allocation and leftover-cent rounding

### What did we do?

Replaced the allocator with `capped_proportional_largest_remainder_v2`. It never scales underclaims upward, records unallocated funds, and assigns rounding cents by fractional remainder rather than total claim size.

### Why did we do it?

The professor identified two problems with the original rule: it spent surplus money that nobody requested, and its leftover-cent convention systematically favored the largest claimant. The revised rule separates the budget available from the budget actually requested and uses a more neutral rounding rule.

### How did we do it?

For five valid final claims:

1. **Claims total at or below budget:** pay each claim down to whole cents and leave the remaining budget unallocated. Do not scale up.
2. **Claims exceed budget:** calculate exact proportional shares, floor them to cents, and distribute remaining cents in descending fractional-remainder order. Break exact remainder ties by county ID, not claim size.
3. **Never exceed a raw claim.** A county's whole-cent cap is its claim rounded down to cents. Skip capped counties when distributing cents. If no further whole-cent payment fits any claim, retain the remainder as unallocated.
4. **All-zero claims:** validly allocate zero to everyone and leave the full budget unallocated. Missing or invalid claims still leave the allocation unavailable; they are not treated as zero.
5. Save `allocation_cents`, `allocation_sum_cents`, `unallocated_cents`, and the allocator version. Check **allocated + unallocated = budget**, with each allocation nonnegative and no larger than its raw claim.

Exact rational arithmetic determines proportional shares. Fractional-cent claims are preserved in the logs; a payment is never rounded above a request merely to force spending. ID-based tie breaking remains a deterministic tie convention, not randomization.

### What results did we find?

The full suite now has **46 passing tests**, including **500 generated claim/budget cases** checking caps, conservation, and independence from dictionary insertion order. Concrete offline cases include:

| Case | Result |
|---|---|
| Five $1 million claims against a $10 million budget | Pay $1 million each; leave $5 million unallocated |
| All five claims zero | Allocate zero; leave all $10 million unallocated |
| Five $2 million claims against a $10 million budget | Pay exactly $2 million each; no surplus |
| Claims A–E of $0.04, $0.03, $0.02, $0.01, $0 against a $0.03 budget | Allocate 1 cent each to A, B, C; B and C receive rounding cents because their remainders are largest |
| Five equal $1 claims against a $0.03 budget | Allocate 1 cent each to A, B, C by the deterministic tie break |
| Five $0.006 claims against a $0.02 budget | Allocate zero; each claim is below one payable cent, so the 2-cent budget stays unallocated |

Both live diagnostic runs were oversubscribed. Their allocations each summed to exactly **$10 million**, with **zero unallocated funds** and no county paid above its claim. The underclaim and zero-claim branches were verified with controlled arithmetic tests, not observed in these two live runs.

The old September 9 allocations and reports were preserved. The working implementation, tests, README, and implementation plan now describe the revised rule; new runs save its version.

### What does it mean for our project?

This engineering correction is complete. Future underclaim runs will reveal genuinely unrequested funds rather than hiding them through automatic expansion. New rounding behavior removes the specific bias toward the largest claimant, although a deterministic ID tie break still exists at the cent level.

Budget conservation alone does not validate the agents' requests. We must continue examining **raw claims and unallocated amounts**, and distinguish allocator versions when comparing historical outputs.

## 5. Preserve the API failure, continue the same run, and verify the records

### What did we do?

Retained an unexpected API failure, checked model access, and continued the same interrupted diagnostic from its saved state. Added a narrowly scoped continuation path and archived the executed source and timing segments. Then audited both completed runs.

### Why did we do it?

The local-estimate run received an **empty HTTP 404 on Round 2, County B**, after six accepted responses. The existing policy correctly treated a 404 as fatal rather than automatically retrying it. Discarding those six outputs and starting a new run would have replaced an observed result; assuming the failed request was free would have understated uncertainty.

### How did we do it?

The initial run stopped and saved its incomplete summary and all seven attempt records. Two subsequent model-metadata access checks returned the configured model identifier, including the check performed by the continuation command. Those metadata reads are separate from the response-generation counts below. They showed the model was accessible at those times, but do not establish the cause of the original 404.

Added an explicit continuation option restricted to an unchanged diagnostic stopped by an empty 404, with attempts remaining. It validates saved settings, fixture, protocol, and previously sent prompts. It preserves the interrupted summary and original source, reuses the six accepted responses exactly, appends attempt 2 for County B's failed logical call, and completes the four remaining responses. The original failed request keeps its unknown-cost reservation. The second variant then runs once as originally scheduled.

There were **two logical diagnostic runs, not a replacement run or a third variant**. Continuation was an explicit operational decision after the access check, not evidence that arbitrary 404s are transient. No malformed outputs or undesirable claims were regenerated.

New runs archive `pilot_source.py` and its SHA-256; continuation archives its source separately. The batch records the planned protocols, source, settings, dependencies, and spending ledgers. Execution segments distinguish active run time from time spent stopped for investigation and testing. The audit checked the saved prompts, round barrier, percentage conversions, costs, allocations, credential absence, and preservation of pre-interruption outputs.

### What results did we find?

| Metric | Local estimate | County count omitted |
|---|---:|---:|
| Completed logical calls | 10 / 10 | 10 / 10 |
| Response-generation attempts | 11 | 10 |
| Successful responses | 10 | 10 |
| API failures | 1 empty 404 | 0 |
| Additional attempts for a logical call | 1 explicit continuation attempt | 0 |
| Rate limits / parse failures | 0 / 0 | 0 / 0 |
| Known input / output tokens | 4,148 / 659 | 3,621 / 655 |
| Known estimated usage cost | $0.0016204 | $0.0015102 |
| Complete cost/usage coverage | No: failed request supplied no usage | Yes |
| Active monotonic run time | 16.815 seconds over two segments | 11.570 seconds |
| UTC span from first start to final finish | 244.497 seconds, including recovery pause | 11.570 seconds |

The known new usage subtotal is **$0.0031306**, about **0.313 cents**. The full cost is unknown because the 404 supplied no usage. Its **$0.01 retained allowance** is a spending precaution, not an observed charge.

Across all saved live work, the ledger now holds **$0.0127378 known estimated cost**, plus two $0.01 reservations: the earlier September 9 interrupted request and this 404. The combined guard-accounted amount is **$0.0327378**. The $1 local guard remains unchanged; the account's exact remaining credit was not checked.

Prices were rechecked September 17 against [official model pricing](https://developers.openai.com/api/docs/models/gpt-5.6-luna): $0.20 ordinary input, $0.02 cache reads, $0.25 cache writes, and $1.20 output per million tokens. Costs use recorded usage and remain estimates rather than a reconciled provider invoice. The model returned `gpt-5.6-luna` and temperature `1.0` for all 20 successful new responses; no separate dated snapshot identifier was returned.

Active UTC durations and monotonic durations agreed within 0.001 second for these new execution segments. The long first-run UTC span reflects the explicit recovery pause. This does not retroactively explain or correct the timing discrepancy in the original September 9 test. No mixed-protocol cost projection or complete-cost claim is made for this follow-up.

### What does it mean for our project?

The experiment can retain an operational failure without losing the accepted conversation or concealing its cost uncertainty. Live observations remain traceable to full prompts, outputs, and executed source. The new metadata improves auditability, but neither source archiving nor temperature logging makes future LLM responses deterministic.

The failed request also illustrates why successful-run costs alone are insufficient. Future reports should retain failure counts, missing usage, recovery pauses, and the distinction between active runtime and total elapsed time.

## Status and next scientific step

The requested two diagnostic runs, percentage-resolution check, and allocator correction are completed, with the failure and continuation disclosed. The professor's warning about County A's neighbor configuration still applies: **none of these runs shuffles profiles across positions**, so none isolates a network-position effect. The later experiment must hold profiles/need fixed through randomized reassignment across positions rather than treating County A's current behavior as a structural effect.

The evidence supports further small, repeated evaluation of a local-estimate prompt, including attention to A's and B's over-requests; it does not justify claiming that need response is solved. A percentage-only control would help separate output format from the added estimate, and repetitions would be needed to measure stability and plan sample size. Those experiments were not added to this two-run diagnostic scope.

The broader literature search, Pennsylvania data table, later approximately eight-agent pipeline, and causal network-position study remain separate work. No email or external sharing was performed.

## Files and reproduction

- [pilot.py](../../pilot.py): revised allocator, percentage protocols, exact conversion, source/timing metadata, and restricted continuation of the observed failure shape.
- [followup.py](../../followup.py): fixed two-variant schedule and separate diagnostic results.
- [tests/test_update2.py](../../tests/test_update2.py) and [tests/test_pilot.py](../../tests/test_pilot.py): new and updated checks.
- [README.md](../../README.md), [implementation plan](../plans/2026-09-08-stage-01-pilot-implementation.md), and [config.json](../../config.json): current behavior and refreshed pricing date.

The old source was archived under `runs/source_snapshots/before_update2_20260917T210840/`; original September 9 result artifacts were not rewritten. The follow-up folder contains the pre-continuation results and source as well as final results. Run artifacts are Git-ignored and must accompany this report separately if shared for independent review.

Offline verification, with no API calls:

```bash
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B followup.py --demo
```

The live command used was `followup.py --live --env-file .env`, followed by explicit `--continue-batch` for the saved folder after the empty 404. Re-running the live command would make new paid calls; it is not needed to read or reproduce this report's arithmetic. The existing results have been retained without tuning or replacement.
