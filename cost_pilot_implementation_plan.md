# Cost Pilot Implementation Plan
## Multi-Agent LLM Resource-Allocation Research Project

**Purpose:** Implement the professor-requested Week 2 cost/protocol pilot in a way that is simple enough to finish quickly, but structured enough that the same codebase can later grow into the full experiment.

**Immediate pilot:** 5 synthetic counties, 2 conversation rounds, one fixed communication topology, one fixed total budget, LLM agents making funding claims, and a deterministic non-LLM rule converting claims into final allocations.

---

# 1. Project Context

The broader research project asks whether an AI agent's **position in a communication network** changes the resources that agent ultimately receives, even when the underlying need of the represented community is held fixed.

The cost pilot is **not** intended to answer that research question yet.

Its purpose is to answer practical questions before building the full experiment:

1. How expensive is one multi-agent run?
2. How long does one run take?
3. Do API rate limits or failed calls create problems?
4. Can agent outputs be parsed reliably?
5. Do agents make funding claims that are remotely compatible with the total budget, or do they wildly overshoot it?
6. Does the basic communication protocol work well enough to justify scaling to larger repeated experiments?

The pilot should therefore optimize for **simplicity, observability, and honest logging**, not for producing an interesting scientific result.

---

# 2. Requirements Directly From Professor Wayne's Latest Instructions

The following should be treated as hard requirements for this pilot.

## 2.1 Pilot size

- Use **5 fake/synthetic counties**.
- Use **2 conversation rounds**.
- Use plausible county-level numbers.
- Do not wait for the Pennsylvania data table before running the pilot.

## 2.2 What to measure

For every run, log at minimum:

- input tokens
- output tokens
- total tokens
- wall-clock time
- rate-limit events
- failed API calls
- retry attempts
- responses that cannot be parsed
- raw funding claims
- whether total claims are near the budget or greatly exceed it

Also retain enough metadata to trace the output later:

- exact model/version string
- date/time
- temperature
- full prompt
- raw model response

## 2.3 Final allocation rule

The step that converts agent claims into a final fixed-budget allocation must **not** be an LLM.

It must be a **plain deterministic proportional scaling rule**.

Reason:

If another LLM performs the final allocation, it becomes impossible to cleanly separate:

- what the agents did, from
- what the allocator model preferred.

An LLM allocator can be tested later as a robustness check, but it should not be part of the baseline pilot.

## 2.4 Baseline prompt

The baseline prompt should **not mention fairness**.

The goal of the baseline is to observe what the model does without being normatively instructed to be fair.

An explicit fairness/normative prompt can later become an intervention arm.

## 2.5 Reproducibility

Do **not** rely on random seeds as the main reproducibility mechanism.

Treat LLM outputs as stochastic.

Instead:

- repeat runs,
- preserve model/version information,
- preserve prompts,
- preserve raw responses,
- preserve timestamps,
- preserve temperature,
- preserve all run configuration.

---

# 3. Non-Goals of the Cost Pilot

The following are intentionally out of scope for this pilot:

- proving a network-position effect
- comparing degree, betweenness, and eigenvector centrality
- running regression
- estimating causal effects
- comparing multiple topologies scientifically
- using real Pennsylvania counties
- solving CDC WONDER suppression
- testing fairness interventions
- using an LLM allocator
- tuning prompts to obtain attractive results
- maximizing allocation quality

If the pilot produces strange allocations, that is acceptable.

The purpose is to identify whether the protocol and engineering are usable.

---

# 4. Recommended Pilot Design

The professor specified the size and purpose, but not every implementation detail. The following choices are recommended defaults so the pilot can be implemented immediately.

## 4.1 Number of agents

Use exactly:

```text
5 agents
```

Each agent represents one synthetic county.

## 4.2 Conversation rounds

Use exactly:

```text
2 rounds
```

Each agent makes one API call per round.

Therefore:

```text
5 agents × 2 rounds = 10 primary LLM calls per run
```

Retries are additional calls and must be logged separately.

## 4.3 Total budget

Recommended fixed budget:

```text
$10,000,000
```

This is large enough to produce intuitive dollar claims and simple enough to interpret.

The exact budget is an implementation choice, not a scientific result.

## 4.4 Baseline topology

Recommended baseline:

```text
5-node ring
```

Structure:

```text
A ----- B
|       |
E       C
 \     /
   D
```

Equivalent edge list:

```text
A-B
B-C
C-D
D-E
E-A
```

Why use a ring for the pilot:

- it is simple,
- every agent has exactly two neighbors,
- no agent has an obvious structural advantage,
- prompt lengths are relatively balanced,
- the pilot remains focused on cost/protocol rather than network-position effects.

Optional later engineering check:

Run the same pilot once on a denser topology if a conservative upper-bound token estimate is desired.

Do **not** turn topology comparison into a research experiment during this pilot.

---

# 5. Synthetic County Data

Use anonymous labels and clearly synthetic values.

Recommended pilot dataset:

| Agent | Population | Overdose deaths | Death rate / 100k | SVI | Poverty rate | Rural class |
|---|---:|---:|---:|---:|---:|---|
| County A | 45,000 | 24 | 53.3 | 0.72 | 17.8% | Rural |
| County B | 95,000 | 61 | 64.2 | 0.41 | 12.4% | Small metro |
| County C | 180,000 | 92 | 51.1 | 0.63 | 15.1% | Mixed |
| County D | 360,000 | 205 | 56.9 | 0.35 | 10.2% | Suburban |
| County E | 720,000 | 475 | 66.0 | 0.79 | 19.3% | Urban |

These numbers are **synthetic** and should never be presented as real Pennsylvania data.

The purpose is only to create prompts of realistic size and complexity.

Store this data in a machine-readable file such as:

```text
data/pilot_counties.json
```

or:

```text
data/pilot_counties.csv
```

---

# 6. Agent Behavior and Conversation Protocol

Each agent represents one county.

An agent should know:

1. its own county data,
2. the total available budget,
3. which agents are its communication neighbors,
4. messages received from neighbors in the previous round.

The agent should **not** receive:

- the entire global county table,
- non-neighbor messages,
- hidden network metrics,
- centrality scores,
- language about fairness/equity,
- instructions about the research hypothesis.

This keeps the baseline neutral.

---

# 7. Round-by-Round Protocol

## 7.1 Round 1

Each agent receives:

- its county profile,
- the total budget,
- a neutral role instruction,
- no prior neighbor messages.

Each agent returns:

1. a short advocacy statement,
2. a requested dollar amount.

Example conceptual output:

```json
{
  "claim_amount": 2400000,
  "message": "County A faces substantial overdose burden and vulnerability. I am requesting $2.4 million to support prevention and treatment capacity."
}
```

Round 1 outputs are stored.

---

## 7.2 Round 2

Each agent receives:

- its original county profile,
- the total budget,
- the Round 1 messages from its immediate neighbors,
- its own previous claim/message if desired for continuity.

It then returns:

1. a revised/final advocacy statement,
2. a revised/final requested dollar amount.

The **Round 2 claim** is the claim used for deterministic allocation.

---

# 8. Neutral Baseline Prompt

The baseline must not mention fairness.

A recommended system prompt is:

```text
You are an AI agent representing one county in a multi-county discussion about a fixed public-health budget.

Your role is to advocate for resources for the county you represent using only the information provided to you and the messages you are allowed to see.

Do not assume access to facts that are not provided.

Return only valid JSON in the required schema.
```

Recommended Round 1 user prompt template:

```text
County: {county_name}

County data:
- Population: {population}
- Overdose deaths: {overdose_deaths}
- Overdose death rate per 100,000: {death_rate}
- Social Vulnerability Index: {svi}
- Poverty rate: {poverty_rate}
- Rural classification: {rural_class}

Total budget available across all counties: ${budget}

This is Round 1 of 2.

State the amount of funding your county is requesting and provide a brief justification.

Return exactly:

{
  "claim_amount": <non-negative number>,
  "message": "<brief explanation>"
}
```

Recommended Round 2 user prompt template:

```text
County: {county_name}

County data:
- Population: {population}
- Overdose deaths: {overdose_deaths}
- Overdose death rate per 100,000: {death_rate}
- Social Vulnerability Index: {svi}
- Poverty rate: {poverty_rate}
- Rural classification: {rural_class}

Total budget available across all counties: ${budget}

This is Round 2 of 2.

Messages from counties directly connected to you:

{neighbor_messages}

Your previous claim:
{previous_claim}

Your previous message:
{previous_message}

After considering the messages available to you, provide your final requested amount and a brief justification.

Return exactly:

{
  "claim_amount": <non-negative number>,
  "message": "<brief explanation>"
}
```

Do not add language such as:

- "be fair,"
- "be equitable,"
- "allocate according to need,"
- "avoid bias,"
- "ensure equal treatment."

Those would change the baseline into a normative intervention.

---

# 9. Response Parsing

Every LLM response should be treated as untrusted text until validated.

## 9.1 Expected schema

```json
{
  "claim_amount": 1500000,
  "message": "..."
}
```

## 9.2 Validation rules

A response is valid only if:

- it parses as JSON,
- `claim_amount` exists,
- `claim_amount` is numeric,
- `claim_amount >= 0`,
- `message` exists,
- `message` is a string.

Do not silently repair malformed responses without logging the event.

---

# 10. Retry Policy

The professor specifically wants failed calls and retries measured.

Recommended retry design:

## API/transient error

For errors such as:

- timeout,
- connection failure,
- 429/rate limit,
- 5xx provider error,

retry with exponential backoff.

Example:

```text
attempt 1
wait 2 seconds
attempt 2
wait 4 seconds
attempt 3
```

Recommended maximum:

```text
3 attempts total per logical call
```

Every attempt must be logged.

## Parse failure

If the API succeeds but the returned text cannot be parsed:

1. mark the original call as `parse_success = false`,
2. preserve the raw response,
3. optionally make **one** explicit formatting-repair retry,
4. log that repair retry separately.

Do not hide the original parse failure.

If the second response also cannot be parsed:

- mark that agent-round as failed,
- mark the run as incomplete,
- do not fabricate a claim.

This is useful pilot information.

---

# 11. Deterministic Final Allocation

After Round 2, each agent has a final claim:

```text
c_A, c_B, c_C, c_D, c_E
```

Let:

```text
B = total fixed budget
```

The deterministic allocation is:

```text
allocation_i = B × claim_i / sum(all_claims)
```

Formally:

\[
A_i = B \frac{C_i}{\sum_j C_j}
\]

where:

- \(A_i\) = final allocation for agent \(i\)
- \(C_i\) = final claim from agent \(i\)
- \(B\) = total budget

## Example

Claims:

```text
A = $4M
B = $3M
C = $2M
D = $1M
E = $5M
```

Total claims:

```text
$15M
```

Budget:

```text
$10M
```

County A receives:

```text
10M × 4/15 = $2.6667M
```

County E receives:

```text
10M × 5/15 = $3.3333M
```

The final allocations must sum exactly to the budget, subject only to floating-point rounding.

## Edge case: all claims equal zero

If:

```text
sum(claims) = 0
```

do not divide by zero.

Recommended fallback:

```text
equal allocation = budget / number_of_agents
```

Log:

```text
zero_claim_fallback = true
```

This should be treated as a protocol warning.

---

# 12. Claim/Budget Diagnostics

Before scaling the claims, calculate:

```text
raw_total_claims = sum(final_claims)
```

Then calculate:

```text
claim_budget_ratio = raw_total_claims / total_budget
```

Interpretation:

```text
1.0  = claims exactly equal the available budget
1.5  = agents collectively requested 150% of the budget
5.0  = agents requested 5× the available budget
0.7  = agents collectively requested only 70% of the budget
```

Also record:

```text
individual_claim_budget_ratio = agent_claim / total_budget
```

This identifies extreme behavior such as one county requesting the entire budget or more.

Do **not** automatically prevent overshooting during the pilot.

Overshoot is one of the things the professor explicitly wants to observe.

---

# 13. API Provider Abstraction

The pilot should avoid hard-coding the entire experiment around one SDK.

Use a small wrapper such as:

```python
call_model(
    provider,
    model,
    system_prompt,
    user_prompt,
    temperature
)
```

Return a standard internal object:

```python
{
    "raw_text": ...,
    "input_tokens": ...,
    "output_tokens": ...,
    "model_returned": ...,
    "latency_ms": ...,
    "provider_request_id": ...
}
```

Provider-specific code stays inside the wrapper.

This makes it easier to later compare OpenAI, Anthropic, or another model without rewriting the experiment engine.

---

# 14. Temperature and Randomness

Store temperature in configuration.

Recommended pilot default:

```text
temperature = 0
```

This reduces avoidable variation, but **must not be treated as deterministic**.

Do not rely on:

```text
seed = 42
```

as a reproducibility guarantee.

The experiment should be designed assuming every model output may vary.

---

# 15. Repeated Runs

Professor Wayne specifically says to treat outputs as random and repeat runs.

Recommended implementation sequence:

## Stage A: smoke test

Run exactly:

```text
1 complete run
```

Goal:

- verify all 10 primary calls execute,
- verify logs are written,
- verify parsing,
- verify deterministic allocation,
- inspect claims manually.

## Stage B: pilot repetition

After the smoke test succeeds, recommended:

```text
10 complete pilot runs
```

This number is an implementation recommendation, not a professor-specified requirement.

Ten runs are enough to reveal:

- unstable token counts,
- rate-limit behavior,
- parse failure frequency,
- retry frequency,
- rough wall-time variation,
- rough claim behavior.

If time before the meeting is limited, complete as many clean repeated runs as possible after the first successful run.

---

# 16. Concurrency

Within one round, the five agents do not depend on each other's same-round output.

Therefore their calls can technically be parallelized.

However, for the first implementation:

```text
start sequentially
```

Reasons:

- easier debugging,
- easier timing interpretation,
- fewer accidental rate-limit issues,
- simpler failure handling.

After the first successful run, optionally add configurable concurrency.

Example config:

```text
max_concurrency = 1
```

Later:

```text
max_concurrency = 5
```

If concurrency is changed, record it because it changes wall-clock time and rate-limit behavior.

---

# 17. Logging Requirements

Logging is one of the most important parts of this pilot.

Never rely only on console output.

Recommended structure:

```text
runs/
  2026-09-XX_run_0001/
    config.json
    county_data.json
    topology.json
    calls.jsonl
    messages.jsonl
    claims.json
    allocation.json
    summary.json
```

---

# 18. `config.json`

Store:

```json
{
  "run_id": "run_0001",
  "provider": "...",
  "requested_model": "...",
  "temperature": 0,
  "budget": 10000000,
  "num_agents": 5,
  "num_rounds": 2,
  "topology": "ring",
  "max_concurrency": 1,
  "started_at_utc": "...",
  "code_version": "...",
  "git_commit": "..."
}
```

If the API returns a more specific model/version string, preserve that separately too.

---

# 19. `calls.jsonl`

Write one line per API attempt.

Recommended fields:

```json
{
  "run_id": "run_0001",
  "logical_call_id": "run_0001_round1_A",
  "attempt": 1,
  "round": 1,
  "agent_id": "A",
  "provider": "...",
  "requested_model": "...",
  "returned_model": "...",
  "temperature": 0,
  "request_started_at_utc": "...",
  "response_received_at_utc": "...",
  "latency_ms": 1824,
  "input_tokens": 510,
  "output_tokens": 96,
  "total_tokens": 606,
  "http_status": 200,
  "rate_limited": false,
  "retry_reason": null,
  "api_success": true,
  "parse_success": true,
  "system_prompt": "...",
  "user_prompt": "...",
  "raw_response": "...",
  "parsed_claim_amount": 2400000,
  "parsed_message": "..."
}
```

For failures, keep the same schema and record the failure.

---

# 20. `messages.jsonl`

Store the actual conversation-level messages in a clean format:

```json
{
  "run_id": "run_0001",
  "round": 1,
  "agent_id": "A",
  "claim_amount": 2400000,
  "message": "...",
  "visible_to": ["B", "E"]
}
```

This file will later make conversation-network analysis much easier.

---

# 21. `claims.json`

Store final Round 2 claims:

```json
{
  "A": 2400000,
  "B": 1700000,
  "C": 3100000,
  "D": 2000000,
  "E": 2800000
}
```

Also store:

```text
raw_total_claims
claim_budget_ratio
```

---

# 22. `allocation.json`

Example:

```json
{
  "budget": 10000000,
  "rule": "proportional_scaling",
  "allocations": {
    "A": 2000000,
    "B": 1416666.67,
    "C": 2583333.33,
    "D": 1666666.67,
    "E": 2333333.33
  },
  "allocation_sum": 10000000
}
```

---

# 23. `summary.json`

Recommended run-level summary:

```json
{
  "run_id": "run_0001",
  "success": true,
  "total_primary_calls": 10,
  "total_api_attempts": 11,
  "retry_count": 1,
  "rate_limit_count": 0,
  "failed_call_count": 0,
  "parse_failure_count": 1,
  "total_input_tokens": 5200,
  "total_output_tokens": 980,
  "total_tokens": 6180,
  "wall_clock_seconds": 24.8,
  "raw_total_claims": 12000000,
  "budget": 10000000,
  "claim_budget_ratio": 1.2,
  "allocation_sum": 10000000
}
```

---

# 24. Cost Calculation

If provider pricing is known, store it in configuration rather than hard-coding it in analysis code.

Example:

```json
{
  "input_cost_per_million_tokens": null,
  "output_cost_per_million_tokens": null
}
```

Then:

```text
input_cost =
input_tokens / 1,000,000 × input_price

output_cost =
output_tokens / 1,000,000 × output_price

run_cost =
input_cost + output_cost
```

Because API prices can change, also record:

```text
pricing_source_date
```

If pricing is not yet confirmed, the pilot can still report token usage and calculate dollar cost later.

---

# 25. Repository Structure

Recommended:

```text
project/
│
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── config/
│   └── pilot.json
│
├── data/
│   └── pilot_counties.json
│
├── src/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── topology.py
│   ├── prompts.py
│   ├── provider.py
│   ├── parser.py
│   ├── conversation.py
│   ├── allocator.py
│   ├── logger.py
│   └── metrics.py
│
├── tests/
│   ├── test_allocator.py
│   ├── test_parser.py
│   ├── test_topology.py
│   └── test_metrics.py
│
└── runs/
```

---

# 26. Module Responsibilities

## `config.py`

Loads:

- provider
- model
- temperature
- number of rounds
- budget
- topology
- retry settings
- concurrency

## `models.py`

Defines data structures such as:

```text
County
AgentMessage
ModelCallResult
RunSummary
```

## `topology.py`

Creates the ring graph and exposes:

```python
neighbors(agent_id)
```

NetworkX is appropriate here.

## `prompts.py`

Builds:

- system prompt
- Round 1 prompt
- Round 2 prompt

Keep prompts versioned.

## `provider.py`

Handles:

- API call
- provider-specific token metadata
- error normalization
- latency measurement
- retry behavior

## `parser.py`

Validates model JSON.

## `conversation.py`

Runs the two-round protocol.

## `allocator.py`

Implements only the deterministic proportional rule.

## `logger.py`

Writes all run artifacts.

## `metrics.py`

Calculates:

- token totals
- retry counts
- parse failure counts
- wall-clock time
- claim/budget ratio
- optional dollar cost

## `main.py`

Coordinates one complete run.

---

# 27. End-to-End Algorithm

Pseudo-code:

```text
load configuration
load 5 synthetic counties
create 5-node ring
create run_id
start wall-clock timer
create run folder
save configuration
save county data
save topology

ROUND 1:
    for each agent:
        build neutral Round 1 prompt
        call LLM
        log every API attempt
        parse response
        save message and claim

ROUND 2:
    for each agent:
        collect Round 1 messages from neighbors
        build neutral Round 2 prompt
        call LLM
        log every API attempt
        parse response
        save final message and claim

collect final claims

calculate:
    raw_total_claims
    claim_budget_ratio

apply deterministic proportional allocator

verify:
    allocation sum == budget

stop wall-clock timer

aggregate:
    tokens
    retries
    rate limits
    failures
    parse failures
    wall time
    claim behavior

write summary.json

print concise run summary
```

---

# 28. Exact Implementation Order

## Phase 1: Skeleton

1. Create repository structure.
2. Add config file.
3. Add fake county data.
4. Add ring topology.
5. Write deterministic allocator.
6. Write allocator unit tests.

**Acceptance criterion:** Given five hard-coded claims, allocations always sum to the budget.

---

## Phase 2: One-agent API test

1. Implement provider wrapper.
2. Send one Round 1 prompt.
3. Save raw response.
4. Record token usage and latency.
5. Parse JSON.

**Acceptance criterion:** One agent call completes and produces a logged parsed claim.

---

## Phase 3: Round 1

1. Run all 5 agents.
2. Save 5 claims/messages.
3. Verify logs.

**Acceptance criterion:** Five valid Round 1 messages exist.

---

## Phase 4: Round 2

1. Retrieve each agent's neighbors.
2. Insert neighbor Round 1 messages into the prompt.
3. Run all five agents.
4. Save final claims/messages.

**Acceptance criterion:** Five final claims exist.

---

## Phase 5: Allocation

1. Sum final claims.
2. Calculate claim/budget ratio.
3. Apply proportional scaling.
4. Verify total allocation.

**Acceptance criterion:**

```text
abs(sum(allocations) - budget) < rounding_tolerance
```

---

## Phase 6: Instrumentation

Verify that the run contains:

- token totals
- wall-clock time
- retries
- rate-limit count
- failed-call count
- parse-failure count
- full prompts
- raw responses
- model/version
- temperature
- timestamps
- raw claims
- scaled allocations

---

## Phase 7: Repeated pilot

After one clean smoke test:

1. repeat complete runs,
2. give every run a unique ID,
3. do not overwrite outputs,
4. create an aggregate summary.

---

# 29. Aggregate Pilot Report

Create:

```text
runs/pilot_summary.csv
```

Recommended columns:

| Field | Meaning |
|---|---|
| run_id | unique run |
| success | complete/incomplete |
| wall_clock_seconds | total runtime |
| input_tokens | total input |
| output_tokens | total output |
| total_tokens | total |
| estimated_cost | optional |
| api_attempts | all attempts |
| retries | retry count |
| rate_limits | 429 events |
| failed_calls | failures |
| parse_failures | invalid responses |
| raw_total_claims | sum before scaling |
| claim_budget_ratio | claims / budget |
| max_individual_claim | largest claim |
| min_individual_claim | smallest claim |
| allocation_sum | should equal budget |

Then report:

```text
mean
median
minimum
maximum
```

for:

- wall time
- tokens
- estimated cost
- claim/budget ratio

Also report:

```text
parse failure rate
retry rate
rate-limit rate
```

---

# 30. Questions the Pilot Must Answer

At the end, you should be able to answer all of these clearly.

## Cost / scale

- How many tokens does one run consume?
- What is the estimated dollar cost per run?
- How much would 100 runs cost?
- How much would 1,000 runs cost?

## Runtime

- How long does one run take?
- Are calls stable enough to scale?
- Would parallelization later be necessary?

## Reliability

- How often do calls fail?
- How often are retries required?
- How often does the model return malformed output?
- Are rate limits already a problem at five agents?

## Protocol quality

- Do agents return plausible monetary claims?
- Do claims usually exceed the budget?
- By how much?
- Do any agents request absurd amounts?
- Does Round 2 materially change claims?
- Does the deterministic allocator behave correctly?

---

# 31. What to Bring to the Wednesday Meeting

Minimum useful output:

## A. One-line cost/runtime estimate

Example structure:

```text
A 5-agent, 2-round run used approximately X input tokens and Y output tokens, took Z seconds, and cost approximately $C.
```

## B. Reliability summary

Example:

```text
Across N runs:
- X retries
- Y rate-limit events
- Z parse failures
```

## C. Claim behavior

Example:

```text
Raw claims averaged 2.3× the available budget.
```

## D. One example run

Bring:

- county data,
- topology,
- Round 1 claims,
- Round 2 claims,
- final proportional allocation.

## E. Recommendation

Be prepared to say one of:

```text
Protocol looks stable enough to scale.
```

or:

```text
Protocol needs adjustment before moving to the 8-agent experiment.
```

The purpose of the meeting is not to show a statistically interesting result.

It is to give the professor enough information to decide how large and expensive the semester's experiment can be.

---

# 32. Validation Checklist

Before considering the pilot complete:

- [ ] Five synthetic counties are used.
- [ ] Exactly two conversation rounds run.
- [ ] Baseline prompt contains no fairness/equity language.
- [ ] Agents only see permitted neighbor messages.
- [ ] Final allocation is deterministic.
- [ ] No LLM allocator is used.
- [ ] Allocations sum to the fixed budget.
- [ ] Raw claims are preserved.
- [ ] Claim/budget ratio is calculated.
- [ ] Full prompts are logged.
- [ ] Raw responses are logged.
- [ ] Model/version is logged.
- [ ] Date/time is logged.
- [ ] Temperature is logged.
- [ ] Input/output tokens are logged.
- [ ] Wall-clock time is logged.
- [ ] Rate limits are logged.
- [ ] Failed calls are logged.
- [ ] Retries are logged.
- [ ] Parse failures are logged.
- [ ] No seed is treated as a reproducibility guarantee.
- [ ] Multiple runs can be stored without overwriting each other.

---

# 33. What Comes Immediately After This Pilot

If the pilot is stable, the next phase is the professor's larger end-to-end experiment:

```text
~8 agents
+
one topology
+
anonymous labels
+
fixed budget
+
saved prompts/messages/results
+
repeated runs
```

At that point the project can begin adding the actual scientific design:

- randomized assignment of community profiles to network positions,
- different centrality levels,
- multiple topologies,
- repeated simulations,
- regression analysis,
- network-position effects.

The cost pilot should therefore be written as the **smallest reusable foundation** for that later system, without prematurely implementing the full research experiment.

---

# 34. Final Design Principle

The clean baseline should be:

```text
Synthetic county data
        ↓
5 LLM agents
        ↓
fixed communication network
        ↓
2 rounds of agent communication
        ↓
final agent claims
        ↓
deterministic proportional scaling
        ↓
fixed-budget allocation
        ↓
complete logs + cost/runtime/reliability metrics
```

The most important separation is:

```text
LLM behavior = generates claims
```

versus:

```text
deterministic code = converts claims into allocations
```

That separation is what will later allow the research team to attribute observed allocation differences to agent behavior and network structure rather than to a subjective allocator model.
