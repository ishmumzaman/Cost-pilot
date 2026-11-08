# Stage 01 — Live pilot report

**Date:** 2026-09-09 (test date).  
**Stage:** 01.  
**Status:** Completed historical report.  
**Former filename:** `live_test_report.md`.

**Test date:** September 9, 2026 (UTC and America/New_York).  
**Scope:** Five synthetic county agents, two rounds, one development smoke test followed by five fixed measured attempts.  
**Primary batch:** `batch_20260909T043530_41863619`.  
**Evidence:** [Generated run report](../../runs/live/batch_20260909T043530_41863619/report.md), [batch statistics](../../runs/live/batch_20260909T043530_41863619/report.json), [artifact validation](../../runs/live/batch_20260909T043530_41863619/validation.json), and the individual run files linked below. This report analyzes existing saved results; no additional paid API calls were made to prepare it.

## 1. What the test established

The initial cost pilot worked end to end. The fresh batch completed **6 of 6 runs and 60 of 60 API calls**, including one development run and five measured runs. All returned claims were usable, all five-county final allocations were computed deterministically, and every allocation summed to exactly **$10,000,000.00**.

Across the five measured runs, the mean cost was **$0.0015604 per run**, with **3,576.8 input tokens and 704.2 output tokens** on average. The mean recorded monotonic run duration was **15.064 seconds**, ranging from **13.236 to 19.356 seconds**. One run has a discrepancy between its UTC timestamp span and monotonic duration; Section 5 documents it rather than treating the timing evidence as perfectly consistent.

The fresh six-run batch cost an estimated **$0.0093492**, less than one cent. There were no observed API failures, rate limits, retries, refusals, truncated responses, or parse failures in that batch. These are observed counts from a small sequential sample, not guarantees about future reliability.

Claims exceeded the budget in every measured round: by **13% on average in Round 1** and **8.2% in Round 2**. The allocator normalized those claims successfully. This answers the professor's early protocol question: claims were close to the budget's scale, but did not add up to it on their own.

**Completion assessment:** The initial five-county cost-pilot deliverable is ready to share, with the timing and billing limitations below. The professor's broader assignment is not finished: the literature follow-up, real Pennsylvania table, and later approximately eight-agent pipeline remain separate work. This report has not been emailed or otherwise sent to the professor.

## 2. Experimental setup and controls

| Setting | Executed configuration |
|---|---|
| Provider / endpoint | OpenAI Responses API |
| Requested / returned model | `gpt-5.6-luna` / `gpt-5.6-luna` in all 60 responses |
| Reasoning effort | `none` |
| Temperature | Omitted from requests; API returned `1.0` in every response |
| Maximum output tokens | 512 per call |
| Service tier | Requested and returned `default` |
| Execution | Sequential, one request at a time; plain Python |
| Conversation handling | Explicit prompt context per call; `store=false`; no seed |
| Tools / streaming / output format | No tools, nonstreaming, ordinary text prompted to contain JSON |
| SDK / Python | OpenAI SDK 2.48.0; Python 3.9.6 |
| Timeout | 60 seconds per request |
| Retry policy | SDK retries disabled; at most 3 total attempts per logical call; manual waits of 2 and 4 seconds, honoring a larger provider retry delay within the configured limit |
| Simulated allocation budget | $10,000,000; this is not API spending |
| Local API spending guard | $1 estimated spend, including retained allowances for unknown costs |
| Measured sample | 5 fixed run attempts after a successful smoke test; failures would not be replaced |

The graph was the undirected ring **A–B–C–D–E–A**, so each county had two neighbors. Agent calls followed A, B, C, D, E in each round. County profiles and graph positions were held fixed across runs; there was no randomized reassignment or topology comparison.

Each Round 1 prompt contained only the county's own profile, its neighbor IDs, the five-county count, the shared budget, and the request for a claim and short justification. Round 2 added the county's own prior response and its two neighbors' Round 1 claim/message records. All five Round 1 responses had to complete before any Round 2 call. No agent received the complete county table, non-neighbor transcripts, or another agent's same-round response. Round 2 was the final discussion round.

The system prompt told agents to advocate for their county using the available information. It contained no explicit fairness objective or instruction to allocate by a specified need metric. The deterministic proportional allocation rule was not disclosed to the agents. These are baseline protocol choices; they do not imply that the model has no learned normative preferences.

### Synthetic county inputs

The input values were made up for the pilot. They are not Pennsylvania estimates and should not be cited as epidemiological data. Mortality represents synthetic single-year **all-drug-overdose deaths**, with a crude annual rate per 100,000; SVI is a synthetic 0–1 score and poverty is a percentage. This fixture choice does not resolve the case definition for the eventual real-data table.

| County | Population | Deaths | Rate per 100,000 | SVI | Poverty % | Rural classification |
|---|---:|---:|---:|---:|---:|---|
| A | 45,000 | 24 | 53.3 | 0.72 | 17.8 | Rural |
| B | 95,000 | 61 | 64.2 | 0.41 | 12.4 | Small metro |
| C | 180,000 | 92 | 51.1 | 0.63 | 15.1 | Mixed |
| D | 360,000 | 205 | 56.9 | 0.35 | 10.2 | Suburban |
| E | 720,000 | 475 | 66.0 | 0.79 | 19.3 | Urban |

## 3. Run-by-run results

S is the successful development smoke test. M1–M5 are the measured runs; the development result is excluded from measured averages and projections. Input/output counts are provider-reported billable usage categories; total tokens equal their sum. Costs are usage-based estimates in USD.

| Run | Completed calls | Input tokens | Output tokens | Total tokens | Estimated cost | Recorded monotonic seconds | R1 claims / budget | R2 claims / budget |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [S](../../runs/live/20260909T043530_development_8836c73c33/summary.json) | 10 / 10 | 3,566 | 695 | 4,261 | $0.0015472 | 18.096 | 1.14 | 1.14 |
| [M1](../../runs/live/20260909T043548_measured_80905026db/summary.json) | 10 / 10 | 3,587 | 703 | 4,290 | $0.0015610 | 14.464 | 1.13 | 1.06 |
| [M2](../../runs/live/20260909T043602_measured_b12813b646/summary.json) | 10 / 10 | 3,572 | 701 | 4,273 | $0.0015556 | 19.356 | 1.14 | 1.07 |
| [M3](../../runs/live/20260909T043628_measured_e4ad7f1e98/summary.json) | 10 / 10 | 3,578 | 691 | 4,269 | $0.0015448 | 13.236 | 1.14 | 1.14 |
| [M4](../../runs/live/20260909T043641_measured_b4328baf1f/summary.json) | 10 / 10 | 3,575 | 708 | 4,283 | $0.0015646 | 13.874 | 1.14 | 1.09 |
| [M5](../../runs/live/20260909T043655_measured_514ad37114/summary.json) | 10 / 10 | 3,572 | 718 | 4,290 | $0.0015760 | 14.392 | 1.1 | 1.05 |

All six runs finished with `run_status=completed`, full reported token/cost coverage, zero retries, and no stop reason. Every run comprised ten separate county-agent calls; there was no eleventh LLM allocator call.

| Metric across M1–M5 | Mean per run | Minimum | Maximum | Total |
|---|---:|---:|---:|---:|
| Input tokens | 3,576.8 | 3,572 | 3,587 | 17,884 |
| Output tokens | 704.2 | 691 | 718 | 3,521 |
| Total tokens | 4,281.0 | 4,269 | 4,290 | 21,405 |
| Estimated cost USD | $0.0015604 | $0.0015448 | $0.0015760 | $0.0078020 |
| Monotonic duration, seconds | 15.064 | 13.236 | 19.356 | 75.322 |

Because all five measured attempts completed, the completed-run-only statistics equal the all-measured-attempt statistics. There is no failed measured-run overhead hidden by selecting successes.

## 4. Cost accounting and credit usage

The saved pricing snapshot is dated September 8, 2026, and was rechecked against the [official model pricing](https://developers.openai.com/api/docs/models/gpt-5.6-luna) on September 9. Per million tokens, the rates are $0.20 ordinary input, $0.02 cache reads, $0.25 cache writes, and $1.20 output. Cache categories must be subtracted from total input before pricing the ordinary-input portion.

Every response in the fresh batch reported zero cache-read and zero cache-write tokens. Consequently, the measured-batch calculation reduces to:

```text
Input:  17,884 / 1,000,000 × $0.20 = $0.0035768
Output:  3,521 / 1,000,000 × $1.20 = $0.0042252
Measured batch total              = $0.0078020
Per completed measured run        = $0.0078020 / 5 = $0.0015604
```

| Spending population | Estimated known cost |
|---|---:|
| Five measured runs | $0.0078020 |
| Successful development smoke test | $0.0015472 |
| Fresh batch: smoke test plus five measured runs | **$0.0093492** |
| Two completed calls in the earlier interrupted development run | $0.0002580 |
| All saved live attempts: known subtotal | **$0.0096072** |
| Additional interrupted call | Unknown actual charge; $0.01 retained allowance |

The earlier attempt is documented in [its own report](../../runs/live/batch_20260909T043335_3b06e868/report.md). It dispatched three calls: two succeeded, then the third was interrupted and its outcome/usage remained unknown. Its summary records `keyboard_interrupt`; the logs do not establish who or what caused the interruption. No measured runs started in that earlier batch.

Across both live batches, this means **63 dispatched attempts: 62 known successful responses and one unknown outcome**. The two development attempts comprise one completed smoke run and one interrupted run; the measured population remains exactly five attempts, all completed. An unknown response is not a demonstrated API failure and is not assumed free.

The [persistent spending ledger](../../runs/live/spend.json) retains $0.0096072 in known estimated cost and $0.01 for the unresolved request, for a combined guard-accounted amount of **$0.0196072**. The allowance is not an observed bill and is not a guaranteed upper bound on the provider's invoice. The exact account balance was not checked, so this report does not claim a verified remainder of the user's $5 credit. Known estimated usage is well below that amount and below the $1 local guard.

For repeated **five-agent, two-round runs with this same configuration**, simple extrapolation gives:

| Number of run attempts | Estimated API cost, excluding development |
|---|---:|
| 100 | $0.15604 |
| 1,000 | $1.5604 |

These are projections from five observed runs, not reserved prices or authorized future spending. They assume comparable prompts, output lengths, pricing, and retry experience. The 1,000-run projection exceeds the current script's $1 guard; it is not something the current invocation is configured to execute. Eight-agent or larger networks, more rounds, another model, or concurrent requests require a new measurement.

### Cost by discussion round

| Across the five measured runs | Input tokens | Output tokens | Estimated cost |
|---|---:|---:|---:|
| Round 1 | 5,915 | 1,740 | $0.0032710 |
| Round 2 | 11,969 | 1,781 | $0.0045310 |

Round 2 used about twice as many input tokens because it included the permitted prior messages; output usage changed little. This makes conversation-context growth a concrete consideration for later scaling.

## 5. Runtime and the timing discrepancy

The runner measures elapsed duration with a monotonic timer around the run, including setup, API calls, validation, allocation, and summary construction. Final summary serialization and batch report generation are outside that metric. Separate UTC timestamps are also saved, with slightly different start/end boundaries. The 15.064-second mean above refers specifically to the saved **monotonic** run durations.

For M2, the saved UTC timestamps are `2026-09-09T04:36:02.969277+00:00` to `2026-09-09T04:36:28.272232+00:00`, a **25.303-second** span. Its monotonic duration is **19.356 seconds**, a difference of **5.947 seconds**. In the other measured runs, UTC spans are roughly 0.015–0.029 seconds shorter than the monotonic measurements, consistent with their slightly different measurement boundaries; those small differences do not explain M2's discrepancy.

Summing the five measured runs gives **75.322 seconds of recorded monotonic duration**, versus **81.176 seconds summed from the individual UTC spans**. The corresponding mean UTC span is **16.235 seconds per run**. The full fresh batch's first-run start to last-run finish spans about **99.390 seconds by UTC**, including gaps between runs; it should not be confused with the sum of the run timers.

The existing logs do not establish the cause of the M2 discrepancy. They have been preserved without rewriting timings. The available measurements support an early estimate on the order of 15–16 seconds per five-agent run, with the observed per-run spread noted above. Precise runtime extrapolation should wait for a focused timing check; the discrepancy does not change the saved token counts, claims, or cost arithmetic.

## 6. Reliability and validation

| Observation | Five measured runs | Fresh batch including successful smoke test |
|---|---:|---:|
| Runs completed / started | 5 / 5 | 6 / 6 |
| Successful API responses / dispatched attempts | 50 / 50 | 60 / 60 |
| Observed API failures / dispatched attempts | 0 / 50 | 0 / 60 |
| HTTP 429 rate-limit events / dispatched attempts | 0 / 50 | 0 / 60 |
| Retry attempts | 0 | 0 |
| Parse failures / responses examined | 0 / 50 | 0 / 60 |
| Refusals or incomplete/truncated responses | 0 / 50 | 0 / 60 |
| Unknown usage or response outcomes | 0 / 50 | 0 / 60 |
| Valid final allocations / completed runs | 5 / 5 | 6 / 6 |

The interrupted development call is outside both columns and remains disclosed in Section 4. The live batch did not exercise rate-limit recovery, timeout recovery, or retry exhaustion because none occurred; absence of errors is not a live test of those recovery paths.

The earlier offline verification recorded **36 passing tests** covering parsing, visibility boundaries, allocation rounding, missing/all-zero/extreme claims, retries and failures, refusals/truncation, interruptions, spending reservations, credential redaction, SDK transport behavior, and batch accounting. Those tests used controlled responses and are distinct from live reliability evidence. See [the test suite](../../tests/test_pilot.py).

The saved live artifacts were checked for all 60 fresh-batch responses: permitted county and neighbor context; Round 1 completion before Round 2; fixed request settings; valid raw and parsed outputs; usage and cost reconciliation; raw claim totals/ratios; exact proportional allocations; and preservation of unknown-spend allowances. The configured credential was absent from the saved run artifacts. During preparation of this report, token totals, cost arithmetic, claim ratios, and allocation totals were checked again directly against the saved records.

These checks establish that the observed batch followed the implemented protocol. They do not establish the factual or policy quality of every natural-language justification, nor do they estimate rare-failure rates or concurrent throughput from this small sequential sample.

## 7. What the agents claimed

Raw claims are reported before normalization so that the allocator cannot hide overshoot.

| Measured run | Round 1 total | Round 1 overshoot | Round 2 total | Round 2 overshoot | Change in total claims |
|---|---:|---:|---:|---:|---:|
| M1 | $11,300,000.00 | 13.00% | $10,600,000.00 | 6.00% | $-700,000.00 |
| M2 | $11,400,000.00 | 14.00% | $10,700,000.00 | 7.00% | $-700,000.00 |
| M3 | $11,400,000.00 | 14.00% | $11,400,000.00 | 14.00% | $0.00 |
| M4 | $11,400,000.00 | 14.00% | $10,900,000.00 | 9.00% | $-500,000.00 |
| M5 | $11,000,000.00 | 10.0% | $10,500,000.00 | 5.00% | $-500,000.00 |

Mean total claims fell from **$11.30 million** to **$10.82 million**, a mean reduction of **$480,000**. Average overshoot fell by **4.8 percentage points**, from 13% to 8.2%. Every final raw total still exceeded the $10 million budget; the discussion did not make the agents' claims collectively budget-balanced.

The change was concentrated entirely in County A:

| Measured run | A change | B change | C change | D change | E change |
|---|---:|---:|---:|---:|---:|
| M1 | $-700,000.00 | $0.00 | $0.00 | $0.00 | $0.00 |
| M2 | $-700,000.00 | $0.00 | $0.00 | $0.00 | $0.00 |
| M3 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 |
| M4 | $-500,000.00 | $0.00 | $0.00 | $0.00 | $0.00 |
| M5 | $-500,000.00 | $0.00 | $0.00 | $0.00 | $0.00 |

Of 25 county-level Round 1-to-Round 2 comparisons, **21 claims were unchanged**, **4 decreased**, and **none increased**. All four decreases were County A's. In M3, every claim was unchanged. Averaging absolute changes across all 25 comparisons gives **$96,000**; the 25 observations share five runs and should not be treated as 25 independent experiments.

This is an observed behavior pattern, not proof that communication caused County A to concede. There was no no-message control, no profile randomization, and no alternative topology. All ring positions are structurally equivalent, and county characteristics were not held identical. The pilot therefore cannot identify an advantage from centrality or network position, or establish fairness relative to need.

### Worked example: M1

| County | Round 1 claim | Round 2 claim | Final allocation |
|---|---:|---:|---:|
| A | $2,500,000.00 | $1,800,000.00 | $1,698,113.20 |
| B | $2,100,000.00 | $2,100,000.00 | $1,981,132.07 |
| C | $2,200,000.00 | $2,200,000.00 | $2,075,471.69 |
| D | $2,000,000.00 | $2,000,000.00 | $1,886,792.45 |
| E | $2,500,000.00 | $2,500,000.00 | $2,358,490.59 |

M1's Round 2 claims totaled $10.6 million. Before cent rounding, each raw final claim was multiplied by `10 / 10.6`, approximately `0.943396`, to obtain its allocation. County A reduced its request from $2.5 million to $1.8 million; the other four counties maintained their claims. In its saved Round 2 message, A referred to greater absolute burdens in neighboring counties. This is a model-generated justification, not independent evidence explaining causation.

The deterministic rule is:

```text
allocation_i = total_budget × final_claim_i / sum(final_claims)
```

The implementation uses exact proportional arithmetic, floors each share to cents, then assigns the remaining cents to the largest claimant, breaking ties alphabetically by county ID. In M1, the displayed cent allocations sum to exactly $10,000,000.00. The same conservation check passed for all six completed runs. Exact budget conservation is an allocator property; it does not mean raw claims were budget-compliant or substantively justified.

## 8. Evidence and reproducibility boundaries

Each run has its own saved `config.json`, `calls.jsonl`, and `summary.json`. Together they retain the fixture, topology, prompt templates and complete per-call prompts, raw response bodies, requested and returned model names, returned temperature, timestamps, request IDs, usage, retry/error fields, parsed claims, and final allocation. The graph and profiles were fixed; no seed was sent. Repeated outputs were treated as stochastic, as requested.

The API returned `gpt-5.6-luna` without a separate dated snapshot identifier. The record preserves that exact returned string; it does not invent an immutable version or promise identical outputs on future API calls.

The saved configuration includes Git commit `8862d633cfd36146ac915beea51b4f3d450ed1cd`, but that commit contains only the earlier plan. The implementation files are currently uncommitted, so that commit alone does **not** reconstruct the executed source. Preserve the current script, dependencies, and configuration alongside the run artifacts when handing off the experiment. Full prompts and responses are already saved independently of Git.

The `runs/` folder is Git-ignored. This report's local evidence links work in this workspace; distributing this Markdown file alone would not distribute the raw logs. Share the relevant artifacts deliberately with the report when reproducibility materials are needed. Keep `.env` and its API credential private.

## 9. Are we finished with what Professor Wayne asked?

The distinction is between the **immediate cost pilot** and the **broader research work**. The governing sources are the August 26 email on PDF pages 8–9 and the latest September 6 email on pages 10–11 of the [email thread](../reference/original-professor-correspondence.pdf). September 6 changed the priority, specified a deterministic allocator, removed fairness instructions from the baseline, and replaced expectations of identical outputs with repeated runs and complete logging.

| Immediate cost-pilot requirement | Evidence / assessment |
|---|---|
| Prioritize the pilot over completing the real table | Done: used five synthetic county profiles |
| Five agents and two rounds | Done: ten agent calls per run |
| Measure token usage and runtime | Done, with a disclosed timing discrepancy: per-call usage and per-run monotonic/UTC timing saved |
| Record rate limits, failures, retries, and unparseable responses | Done: attempt logs and counts retained; fresh batch had none; earlier interruption remains separately recorded |
| Check whether claims fit or overshoot the budget | Done: both rounds' raw totals, ratios, and county-level changes reported |
| Deterministic proportional allocation | Done: no LLM allocator; exact budget conservation verified |
| Baseline without fairness instructions | Done: fixed advocacy prompt without an explicit fairness criterion |
| Repeat runs and treat outputs as stochastic | Done: five fixed measured attempts, separate development runs, no replacement of failures |
| Save model/version string, date, temperature, complete prompts and responses | Done to the extent exposed by the API: exact returned identifier, temperature 1.0, timestamps and raw records saved; no separate dated snapshot was returned |
| Provide an early cost/runtime result for discussion | Result and report ready; delivery to the professor has not been performed here |

**Yes: the initial cost-pilot result is ready for the professor, provided the limitations are included. No: that does not mean every task in his email or the semester project is complete.** No additional large batch or prompt tuning is needed just to deliver this first pilot result.

The remaining work is:

1. **Share the pilot result and the positioning sentence.** A sentence is prepared in the plan: “Where G-Designer and Shen study topology's effects on collective performance, we study whether an agent's network position changes its individual resource allocation when community need is held fixed.” This follows the professor's proposed distinction; it is not a newly verified novelty claim. No email or external sharing was performed as part of this work.
2. **Do the renewed literature search on individual outcomes by network position.** The pilot did not perform that search. The September 4 summaries were acknowledged positively in the professor's reply; his September 6 request for another targeted search remains separate.
3. **Continue the real Pennsylvania county table.** Pool mortality years within one WONDER query, choose all-drug versus opioid-involved deaths, record the exact NCHS case-definition ICD codes, and document suppression, missing values, and judgment calls. Check the coverage of NCHS model-based estimates if needed; do not patch WONDER gaps with a differently defined state series. These are the professor's pending instructions, not steps completed by the synthetic pilot. The table also needs the population, vulnerability, poverty, rural classification, and adjacency inputs described earlier. No completed real-data table was found in this workspace.
4. **Build the later approximately eight-agent pipeline.** The earlier roadmap calls for around eight agents, one topology, anonymous labels, and complete saved results. The current runner is deliberately fixed to five agents; this later milestone has not been implemented. Its allocator should remain deterministic and its LLM outputs should be evaluated through repetition, following the updated September 6 instructions.

Beyond those near-term tasks, randomized profile placement, topology comparisons, need-adjusted outcome analysis, attention-network extraction, intervention arms, and the Pennsylvania applied case belong to the broader research design. This cost pilot does not claim to have tested the central scientific hypothesis.

## 10. Recommended next step

Use this report for the professor's immediate review: the selected small-model configuration ran successfully and is inexpensive for the tested five-agent protocol, with moderate raw-claim overshoot handled transparently by proportional allocation. State the measured sample size, the earlier unknown request cost, and the timing discrepancy when discussing the result.

Before making precise runtime-based scaling decisions, resolve or recheck the timing discrepancy in a small focused check. Preserve this batch as collected; do not silently replace its timings or claims. Then carry forward the literature/table tasks and the next approximately eight-agent milestone. Avoid changing the baseline prompts merely to produce nicer-looking allocations.
