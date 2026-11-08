# Stage 01 — Pilot implementation plan

**Date:** 2026-09-08 (first tracked Git version; includes later amendments through 2026-09-17).  
**Stage:** 01; historical plan with Stage 02 amendments.  
**Status:** Initial pilot completed; historical follow-ups retain their recorded scope.  
**Former filename:** `cost_pilot_implementation_plan.md`.

## 1. Objective and requirements

Build the smallest useful pilot that tells Professor Wayne how expensive and time-consuming the proposed multi-agent experiment is, whether calls and outputs are reliable, and whether funding claims are remotely compatible with the budget.

**Source:** The August 26 and September 6 emails in the accompanying PDF. The latest email replaces the earlier LLM allocator with a deterministic rule and replaces expectations of identical live outputs with repeated runs and complete logging.

**September 9 feedback, implemented September 17:** The newer email supplied in chat supersedes the initial underclaim and rounding rules. Run the two small percentage-output diagnostics in `followup.py`: one with a hypothetical own-county funding estimate ($10,000 per recorded death), the other with the county-count line omitted. Keep the baseline runs intact. Report claims as budget percentages, their association with deaths, and whether outputs are finer than one percentage point; one run per variant is diagnostic, not a causal estimate. See [Stage 02 report](../reports/2026-09-17-stage-02-follow-up-diagnostics.md) for execution and results. Profile shuffling remains required for the later network-position experiment.

| Professor's requirement | How this pilot meets it |
|---|---|
| Prioritize the cost pilot before finishing the Pennsylvania table | Use five synthetic counties with plausible numbers |
| Five agents and two rounds | Five initial claims, then five responses to neighbor messages |
| Measure tokens and wall-clock time | Record usage per API attempt and elapsed time per run |
| Log rate limits, failed calls, retries, and unparseable outputs | Keep every attempt, including recovered errors and failed runs |
| Check whether claims approach or overshoot the budget | Report raw claim totals divided by the budget before allocation |
| Use deterministic proportional allocation | Apply the formula in Section 3; no allocator LLM |
| Keep the baseline free of fairness instructions | Use the fixed advocacy prompt below |
| Treat model outputs as stochastic and repeat runs | Run a smoke test, then a small fixed batch of measured attempts |
| Preserve model version, date, temperature, full prompts, and raw responses | Save these with the configuration, input data, and results |

The **ring, $10 million simulated budget, one model, sequential execution, and five measured run attempts** are practical defaults, not professor-specified requirements.

This pilot does not test the research hypothesis, compare models/topologies, run regressions, collect real county data, or tune prompts for attractive allocations. It should produce an early number for the Wednesday discussion, even if only the first fully logged run is ready.

**Implementation status:** Implemented in `pilot.py`, with `config.json`, `counties.json`, tests, and setup instructions in `README.md`. Offline protocol and SDK transport checks pass. Live validation on September 9, 2026 completed one smoke test and all five measured runs (60 successful calls; no retries, rate limits, or parse failures). The fresh batch cost an estimated $0.0093492; measured runs averaged $0.0015604 and 15.06 seconds. Raw claims averaged 1.13 times the budget in Round 1 and 1.082 times in Round 2. See [live validation](../reports/2026-09-09-stage-01-validation.md) and its linked report/logs, including the separately retained interrupted development attempt. This completes the initial cost pilot; the research follow-ups below remain separate. Demo outputs are simulated, not research measurements.

## 2. Data and two-round protocol

Use this clearly labeled synthetic fixture. Deaths represent a made-up single-year all-drug-overdose count; rates are crude annual deaths per 100,000. SVI is a synthetic 0-1 value. This does not decide the later real-data case definition.

| County | Population | Deaths | Rate / 100k | SVI | Poverty | Rural class |
|---|---:|---:|---:|---:|---:|---|
| A | 45,000 | 24 | 53.3 | 0.72 | 17.8% | Rural |
| B | 95,000 | 61 | 64.2 | 0.41 | 12.4% | Small metro |
| C | 180,000 | 92 | 51.1 | 0.63 | 15.1% | Mixed |
| D | 360,000 | 205 | 56.9 | 0.35 | 10.2% | Suburban |
| E | 720,000 | 475 | 66.0 | 0.79 | 19.3% | Urban |

**Network:** Undirected ring with edges A-B, B-C, C-D, D-E, E-A.
**Simulated funding budget:** $10,000,000 shared by all five counties.

Each agent knows only its own profile, the shared budget, the number of counties, its neighbor IDs, and the permitted previous-round messages. It does not receive the global county table, non-neighbor messages, centrality scores, or the research hypothesis.

1. **Round 1:** Call each agent once, in A-through-E order, for a numeric claim and a short advocacy message. Each output is the same broadcast to both neighbors.
2. **Round 2:** Only after all five Round 1 outputs are valid, call each agent again with its own previous output and its two neighbors' Round 1 outputs. Include sender ID, numeric claim, and message, ordered by sender ID.
3. **Allocation:** Use the five Round 2 claims. Round 2 messages are terminal outputs; there is no third round.

Round 2 always reads the saved Round 1 snapshot, never another agent's Round 2 output. Build requests explicitly rather than sharing conversation state between agents. This gives ten planned logical calls and one opportunity to react to neighbors. Retries add API attempts; failures can stop a run early.

Keep the profiles, prompts, ordering, model settings, and network unchanged across measured runs. For the initial baseline, do not disclose the allocation formula to agents; record that choice. Any later change is a separate configuration, not part of the same reported batch.

## 3. Prompts, validation, and allocation

Use this system prompt for every agent:

```text
You are an AI agent representing one county in a discussion about a fixed public-health budget.
Your role is to advocate for resources for your county using only the information provided and the messages you are allowed to see.
Do not assume access to facts that are not provided.
Return only JSON with a finite non-negative numeric claim_amount in USD and a short nonempty message string.
```

Use this user template, filling every placeholder:

```text
County: {county_id}
County data: {own_county_profile}
Number of counties sharing the budget: 5
Your directly connected neighbors: {neighbor_ids}
Total budget across all counties: $10,000,000
Round: {round_number} of 2

{round_context}

{round_instruction}
Return a JSON object with exactly these fields:
- claim_amount: your requested amount as a finite non-negative number in USD
- message: your brief justification as a nonempty string
```

- Round 1 context: `No previous messages.` Instruction: `State your requested amount and briefly justify it.`
- Round 2 context: the agent's own previous claim/message plus attributed neighbor ID/claim/message records. Instruction: `After considering the available messages, state your final requested amount and briefly justify it.`
- Add no instructions to be fair, equitable, allocate by need, or avoid bias. Native schema-constrained output and LLM formatting repair are deferred; use ordinary text requested as JSON for this baseline.

**Validation:** Require a JSON object with exactly the two expected fields, a finite nonnegative numeric claim, and a nonempty message string. Reject booleans, numeric strings, NaN/infinity, duplicate keys, extra fields, and malformed responses; do not silently repair them. Record provider-identified refusal or truncation as unusable output. Preserve very large valid claims without capping them to the budget.

**Allocation (revised):** For five valid final claims whose total exceeds the budget:

```text
allocation_i = budget * claim_i / sum(final_claims)
```

If claims total no more than the budget, pay each claim down to whole cents without scaling it up. Leave the rest unallocated and record it. For oversubscribed claims, calculate exact proportional ratios, floor shares to cents, then distribute remaining cents in descending fractional-remainder order, with county ID breaking ties. Never exceed the whole-cent cap of any raw claim; skip capped counties and leave any amount that cannot be paid under those caps unallocated. Verify allocated cents plus unallocated cents equals the budget. This replaces the original scale-up and largest-claimant rounding convention.

If final claims are missing/invalid, leave both allocation and unallocated amount unavailable and mark the run incomplete. Do not substitute equal allocation, earlier claims, or a four-county allocation. All-zero valid final claims now produce zero allocations and the entire budget unallocated in a completed run.

## 4. Logging, failures, and cost

### Selected provider and settings

Use **OpenAI directly through the official Python SDK and Responses API**, with **`gpt-5.6-luna` for all five agents**. This is the inexpensive starting model for this protocol, not a final choice for the research study. If Professor Wayne supplies a different intended model or funded provider account, settle that choice before the measured batch.

| Setting | Initial value |
|---|---|
| Request model | `gpt-5.6-luna` |
| Reasoning | `reasoning.effort = "none"`, explicitly set |
| Maximum output | `max_output_tokens = 512` per request |
| Temperature | Omit the parameter; record `temperature_sent = false` and any returned value |
| Response format | Plain text prompted to return JSON; no native JSON/schema enforcement |
| Tools | None; no browsing or external information |
| Streaming | Off |
| Processing tier | Standard (`service_tier = "default"`) |
| Caching | Leave provider defaults; preserve cache-read/write usage and returned settings |
| SDK request timeout | `timeout = 60.0` seconds |
| SDK automatic retries | `max_retries = 0` |
| Script retry limit | Three total attempts per logical call |
| Script concurrency | `1` |
| Script API spending limit | `$1` estimated total across development and measured calls, separate from simulated funding |

The model supports reasoning `none` but defaults to `medium`, so do not omit the reasoning setting. Its exact temperature compatibility was not established in the documentation review: omission is deliberate, not a claim that temperature is zero. If the response does not expose the effective value, record it as unknown/provider-controlled rather than inventing a number. Save requested and returned model IDs; do not invent a dated snapshot ID. See the [model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna) and [model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6).

Build independent requests with only the explicit context in Section 2; do not use a shared provider conversation or `previous_response_id`. Check API access, accepted settings, and output truncation during development. Adjust the 512-token cap or timeout only if that check reveals an engineering problem, record the change, and freeze the resolved settings before measured runs. Do not switch models because claims look strange.

### Saved results and error handling

Save each started run in its own folder. One JSONL file and two JSON files are sufficient:

```text
runs/run_001/
  config.json     # Actual settings, prompts/templates, county data, and edge list
  calls.jsonl     # One record per API attempt, including errors
  summary.json    # Run outcome, metrics, both rounds' claims, and allocation
```

In `config.json`, save the actual settings above, including the deliberate temperature omission, output-token limit, response format, reasoning/cache settings, timeout, retry settings, and date/time. Record the SDK version and code commit when available. Keep these settings fixed for measured runs; do not rely on seeds or temperature zero to reproduce identical outputs.

For **each API attempt**, save:

- Run ID, county, round, logical-call ID, attempt number, and timestamp.
- Full actual system/user prompts, raw model response, requested/returned model version, and provider request ID when available.
- Reported input/output/total tokens and the original usage metadata, even for malformed output.
- Elapsed call time, API error/status, rate-limit event, retry reason/wait, parsing result, and stop reason when available.

**Retries:** Disable SDK automatic retries so the script can count every attempt. Retry transient connection/timeouts, rate limits, and server errors at most twice: three total attempts per logical call, with 2- then 4-second waits, honoring provider retry-after information. Set an explicit request timeout. If the provider requires a wait longer than the configured 60-second retry-wait limit, stop and log it rather than retrying prematurely. Do not retry invalid credentials or configuration unchanged.

**Terminal failures:** A call that exhausts its retries, or returns unusable output, stops that run. Save the partial results, elapsed time, and failure reason; do not create an allocation. Formatting-repair calls are not part of this pilot. Retain interrupted runs too, with whatever information is available.

**Run summary:** Record completion/incompletion, total API attempts, retry count, failed API attempts (including recovered ones), rate limits, parse/unusable-output failures, and any ultimately failed logical call. Measure wall time with a monotonic timer around the whole run, including retries and backoff. Clearly distinguish a recovered failed attempt from a failed run.

For each complete round, calculate `sum(claims) / budget`. Preserve individual claims, and compare Round 1 with Round 2 using each county's claim change. For a partial round, retain observed claims but do not present its subtotal as a complete five-county ratio. A budget-fitting allocation does not imply sensible claims, and changed claims alone do not prove communication caused the change.

**Dollar cost:** Use provider-reported usage and a dated pricing source saved with the run. The basic uncached formula is:

```text
cost = input_tokens / 1,000,000 * input_price
     + output_tokens / 1,000,000 * output_price
```

The [Luna pricing documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna), checked September 8, 2026, lists these standard short-context rates per million tokens: **$0.20 ordinary input, $0.02 cached input, $0.25 cache writes, and $1.20 output**. Verify and save the rates at execution time. Split reported input into non-overlapping ordinary/cache-read/cache-write categories rather than adding cache charges on top of already-counted input. Keep the original usage object to audit that calculation.

For illustration only, 5,000 ordinary uncached input tokens plus 1,000 output tokens across a run would cost **$0.0022** before any different cache charges or additional attempts. The report must use measured usage, not this example. Its estimate applies to Luna with these settings; another model needs its own measurement.

Count every attempt with reported usage. Use the selected provider's billing categories if cache or other token pricing differs, without double-counting categories. Missing usage after an error is **unknown, not zero**: report the known subtotal and flag incomplete cost coverage. Do not build a general billing engine.

Check the script's $1 estimated spending limit before each request/retry and stop the batch when no allowance remains. It is a local guard, not a guarantee of exact provider billing; unknown usage must not be treated as free. Before live calls, provide `OPENAI_API_KEY` through the environment and confirm the account has API billing and model access. Do not log credentials. These are execution prerequisites, not reasons to expand the plan.

## 5. Smallest implementation and checks

Start with `pilot.py`, `config.json`, `counties.json`, and the `openai` Python package, pinning the working SDK version. A fixed dictionary can represent the ring. Functions for prompt building, calls/logging, validation, allocation, and reporting can all live in the same script initially.

Use sequential plain Python for this first measurement. Professor Wayne mentioned LangGraph earlier; document that it is deferred for the cost pilot. Multiple providers, concurrency, elaborate campaign infrastructure, configuration hashing, crash recovery tooling, and offline replay are not prerequisites.

Implementation order:

1. Add the county fixture, ring, fixed prompts, and proportional allocator.
2. Add response validation and attempt logging **before the first paid request**.
3. Add the provider call with disabled SDK retries, the explicit retry loop, and failure summaries.
4. Run one fully logged development smoke test through both rounds and allocation. Retain any development failures and their costs separately; fix implementation errors, not undesirable claims.
5. Freeze the settings, then make **five measured run attempts**, keeping every outcome. Do not keep running until five successes appear or replace failures. If time/spending stops the batch early, report the actual attempted count and why it stopped.
6. Produce the short report in Section 6. Split the script into modules only when needed later.

Before measured runs, perform a few local checks with fixed/fake responses:

- Claims produce nonnegative allocations no greater than requested, with allocated plus unallocated money summing exactly to the budget; test underclaiming, oversubscription, fractional remainders, sub-cent caps, and individual zero claims.
- All-zero claims leave the whole budget unallocated; missing and malformed claim sets produce no allocation.
- A Round 2 prompt contains only its own previous output and the correct neighbors' Round 1 records.
- A simulated rate limit followed by success counts both attempts; an exhausted retry or malformed response produces an incomplete run and no fabricated claim. Malformed-response usage is retained, and missing usage stays unknown.

Five measured attempts are a practical first sample, not a guarantee of reliability. If only the smoke-test result is ready for the meeting, share it promptly and label its limited scope.

## 6. Report to Professor Wayne and remaining follow-ups

Write one short Markdown report, with one row per measured run:

| Run | Outcome | Input/output tokens | Cost or known subtotal | Wall time | Retries / rate limits / failures | Round 1 ratio | Round 2 ratio |
|---|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... | ... |

Include:

- Model and settings, attempted/completed run counts, and separate development spend.
- Mean and observed range of runtime and token/cost usage. Include failed attempts in operational totals; label completed-run-only averages separately and identify unknown usage.
- Raw reliability counts with denominators: for example, rate-limit events out of API attempts, parse failures out of API-successful responses, and completed runs out of started runs.
- Both rounds' claim/budget ratios, individual claim changes, and one example showing county data, ring, claims, and final allocation.
- When cost coverage is complete, `total measured-batch cost / completed runs` as the effective cost per completed run, including failed-run overhead. This is undefined if no run completes.
- A rough cost for 100 or 1,000 **attempts of the same configuration**. Larger networks, more rounds/neighbors, different models, or parallel execution need new assumptions and a later small check.
- A short recommendation: proceed to a limited eight-agent follow-up, or explain which protocol/engineering issue needs adjustment first. A small sequential sample cannot establish rare-failure rates or concurrent rate-limit behavior.

**Other requests in the September 6 email remain tracked separately; they must not delay the early pilot number:**

- [ ] Share this distinction: "Where G-Designer and Shen study topology's effects on collective performance, we study whether an agent's network position changes its individual resource allocation when community need is held fixed."
- [ ] Search again for research on individual outcomes by network position; record relevant papers and remaining uncertainty before making novelty claims.
- [ ] Resume the Pennsylvania table: pool mortality years within one WONDER query; decide all-drug versus opioid-involved deaths and record exact NCHS case-definition ICD codes; document suppression/missingness. If needed, check the suggested NCHS model-based county estimates and their year coverage. Do not patch WONDER gaps with a state series using a different definition.

**Done for this pilot:** A working five-agent/two-round pipeline, deterministic allocation, honest saved logs, a small repeated-run report, and a clear early cost/runtime estimate or explicitly documented measurement limitation. No interesting scientific result or identical live model outputs are required.
