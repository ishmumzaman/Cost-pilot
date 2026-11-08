# Cost Pilot

## Documentation and current research status

Start with the [documentation index](docs/README.md) for the chronological timeline, current status, and next research work. Reports, plans, professor correspondence summaries, and reference material now live under `docs/`.

Stage 03 is complete. Professor Wayne's [October 17 feedback](docs/updates/2026-10-17-stage-03-feedback.md) defines the pending next stage: a standalone format result, inspection of the 16 changed pairs, repeated communication probes, and a second-model check. The commands below reproduce the existing executable stages; they do not implement those new experiments.

A small implementation of Professor Wayne's five-county, two-round cost/protocol pilot. It uses a fixed ring, county-only information plus previous neighbor messages, a baseline without fairness instructions, and deterministic proportional allocation. The implementation follows [the plan](docs/plans/2026-09-08-stage-01-pilot-implementation.md).

**Status:** Implemented and verified offline and live. On September 9, 2026, one live smoke test and all five measured runs completed: 60 successful API calls, no retries/rate limits/parse failures, and $0.0093492 estimated batch cost. Measured runs averaged 15.06 seconds and $0.0015604 each. See [live validation](docs/reports/2026-09-09-stage-01-validation.md) for evidence, claim behavior, and the separately retained interrupted development attempt. Demo results remain simulated and must not be presented as research measurements.

**Latest follow-up (October 14):** The September 17 feedback is implemented and the fixed Update 3 study is complete: 50 repeated runs plus three paired probes, 533 successful calls, and 59 passing tests. See [Update 3](docs/reports/2026-10-14-stage-03-format-communication.md) for the results and limitations, and [methods](docs/methods.md) for the reproducible procedure.

## Setup

Python 3.9 or later on macOS/Linux. The runner uses a local file lock to prevent concurrent processes sharing the spending ledger.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

No agent framework or database is required. The two direct dependencies are pinned. LangGraph, concurrency, other providers, and the real county table remain deferred.

## Verify without an API key

```bash
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python pilot.py --demo
```

The demo runs one simulated development run and five simulated measured attempts through the same orchestration, logging, validation, allocation, and reporting paths. Its claims and usage are fixtures, and its wall time measures local execution only. Files go under `runs/demo/`, separately from live results.

Tests cover neighbor isolation and the round barrier; strict parsing; exact allocations, overshoot, underclaiming, zero claims and very large values; billed malformed outputs; refusals/truncation; recovered/exhausted retries; unknown usage; interruptions; spending reservations; credential redaction; the installed SDK request/response and retry behavior; and batch/report accounting including failed runs.

## Run the live pilot

Create an ignored `.env` file using `.env.example` and enter `OPENAI_API_KEY` locally. Do not paste the key into chat or commit it. The key needs API billing and access to the configured model. Alternatively, export the variable in the environment.

```bash
.venv/bin/python pilot.py --live --env-file .env
```

With the environment variable already set:

```bash
.venv/bin/python pilot.py --live
```

The command runs **one development smoke test, followed by five measured run attempts**. A failed smoke test prevents the measured batch. Measured failures are retained and never replaced with new successes. Authentication, invalid-model/configuration, insufficient quota, interruptions, spending stops, or excessive retry-after delays stop the batch; unstarted measured runs are counted in the report. Transient or parsing failures within measured runs do not erase the attempt or prevent the next scheduled run unless a batch-stop condition applies.

The script exits 0 only when the smoke test and all scheduled measured runs complete; 1 indicates an incomplete/stopped batch; 2 indicates setup failure. Missing credentials are detected before API requests. It never silently switches models or adds fairness instructions to improve results.

## Configuration

The September 9 feedback is implemented in [Update 2](docs/reports/2026-09-17-stage-02-follow-up-diagnostics.md). Run its two separate diagnostic variants with:

```bash
.venv/bin/python followup.py --demo
.venv/bin/python followup.py --live --env-file .env
```

This performs exactly one five-agent/two-round attempt with a hypothetical local funding estimate, then one with the county count omitted. Both request `claim_percent` (100 means the entire budget); no extra smoke run or replacement run is added. Each live invocation makes new paid calls. It shares the existing live lock and spending ledger. Results and the predeclared schedule go into `runs/live/update2_*/`; individual diagnostic runs remain separate from the historical baseline. The $10,000-per-recorded-death estimate is a synthetic input, not an empirical intervention cost. County labels and neighbor messages can still allow inference about the hidden count.

The live follow-up encountered an empty HTTP 404 after six successful calls. A narrowly scoped `--continue-batch <existing update2 folder>` option verifies model access and permits continuation only for this failure shape, with unchanged saved settings/prompts and attempts remaining. It preserves accepted outputs, appends a new attempt for the failed logical call, archives the interrupted summaries and source, and retains unknown-cost reservations. It does not restart completed runs or repair malformed responses. Continuations record active timing segments separately from the elapsed UTC span, which includes the recovery pause. See `docs/reports/2026-09-17-stage-02-follow-up-diagnostics.md` for the actual event and results; do not rerun it just to reproduce the report.

`config.json` selects OpenAI Responses with `gpt-5.6-luna`, reasoning `none`, 512 maximum output tokens, omitted temperature, a 60-second SDK timeout, sequential requests, and three total API attempts per logical call. SDK retries are disabled; the script waits 2 then 4 seconds, honoring a larger provider retry-after. If the required wait exceeds the configured 60-second maximum, it stops and logs the reason rather than ignoring the provider's request.

Responses use ordinary text prompted as JSON, no tools, no streaming, and the standard service tier. `store=false` avoids using stored Responses conversation state; each request carries exactly the permitted context. Caching remains at provider defaults. No seed is used. Effective temperature and cache settings are preserved when returned; absent values are unknown rather than invented. The September 9 live batch confirmed account/model compatibility: all 60 responses returned `gpt-5.6-luna`, temperature `1.0`, and service tier `default`.

You can adjust the output cap or timeout after a development failure, documenting the change, before collecting a new measured batch. Do not pool different configurations. The model/pricing adapter deliberately supports only this initial Luna configuration. Different providers/models should receive their own later measurement.

`counties.json` is the labeled synthetic fixture, including units. Death rates are checked against deaths/population. Prompts never receive other county profiles or same-round messages.

## Outputs and measurements

Each live run gets a unique folder under `runs/live/`:

- `config.json`: copied settings, input data, ring edges, prompt templates, timestamps, Python/SDK version, code commit when available, and provenance choices.
- `calls.jsonl`: one record per dispatched API attempt, including complete prompts and response bodies, request IDs, usage, timing, retries/errors, and validation. Handled in-flight interruptions retain a record with unknown outcome/usage.
- `summary.json`: run outcome, failures, usage/cost coverage, both rounds' raw claims and budget percentages, paired claim changes, allocated and unallocated cents, and both monotonic/UTC elapsed times. Missing final claims leave allocation and surplus unavailable.
- `pilot_source.py`: exact executed runner source, with its SHA-256 recorded in `config.json`; new runs identify the protocol and allocator version.

Each invocation also creates a `batch_*/report.md` for the meeting and `report.json` for analysis. The printed path points to the report. The Markdown includes the model/settings, individual runs, means/ranges, failure denominators, example fixture/claims/allocation, projections where cost coverage is complete, and limitations. Development spend is separate from measured spend. `spend.json` retains total known costs/reservations across invocations using this output directory.

Claims and costs are stored as **decimal strings** to avoid rounding JSON money through binary floating point. Neighbor prompts serialize claims as numeric JSON values in the requested unit. Percentage responses retain their original `claim_percent` and an exactly derived dollar `claim_amount`. Canonical allocations are integer cents. The revised allocator scales down oversubscribed claims proportionally and distributes rounding cents by largest fractional remainder, ties by county ID, subject to each claim's whole-cent cap. Underclaims are paid without scaling up. Sub-cent amounts that cannot be paid without exceeding a claim remain unallocated. All-zero final claims validly allocate zero and leave the whole budget unallocated; missing claims produce no allocation. Always check allocated cents plus unallocated cents equals budget cents. Historical September 9 artifacts retain the old rule and are not rewritten.

Run wall time uses a monotonic clock and includes setup, calls, validation, retry/backoff, and processing up to final summary construction; it excludes final summary serialization and batch report generation. Durations in a replayed file are observations from that run, not repeated live behavior. This project does not add a replay engine.

## Cost coverage and spending

The configuration contains dated pricing and its official source. Luna cache reads and cache writes are separate parts of the reported input total. The calculation subtracts both before pricing ordinary input, and counts billed output only once. Missing/inconsistent categories, unknown usage, an unexpected model/service tier, or requests outside the configured short-context pricing return an **unknown full cost**, alongside known token/cost subtotals. A malformed model output can still have known billable usage. Failed requests without usage are never assumed free.

The **$1 script spending guard** is separate from the simulated $10 million funding allocation. Before dispatch, it reserves a conservative allowance based on request bytes plus framing allowance and maximum output; each reservation is at least $0.01. Known cost replaces the reservation afterward. Unknown cost keeps its reservation across restarts. The ledger is written before the request so an abrupt crash does not silently free an in-flight allowance. Do not delete/reset the ledger to rerun a failed request. Reconcile uncertain amounts with provider billing before adjusting it.

This guard limits estimated local spend, not the provider's exact invoice. It cannot account for calls made by other software. All development/live invocations from this project use the same live ledger and an exclusive directory lock. Demo reservations use a separate ledger and represent no actual spending.

## Research boundaries

The pilot measures this model and configuration; it does not establish causal network effects, fairness, rare-failure rates, or concurrent throughput. Five small sequential attempts are only an initial sample. Do not replace strange allocations with nicer ones. The professor's renewed literature search and Pennsylvania data-table instructions remain separate follow-ups in the plan; no emails or external sharing are performed by this script.

## Update 3: September 17 feedback

The [implementation plan](docs/plans/2026-09-23-stage-03-need-communication-implementation.md) is implemented by `diagnostics.py`; see [methods](docs/methods.md) for the frozen design and retry/continuation rules. It adds only two prompt conditions and reuses the existing transport, allocator, ledger, and dependencies.

```bash
# Offline shortened campaign: three probes and two blocks of five conditions.
.venv/bin/python diagnostics.py --demo --phase all --demo-blocks 2

# Live fixed study: 40 factorial + 10 reference runs, plus three paired probes.
.venv/bin/python diagnostics.py --live --env-file .env --phase all
```

`--phase stress` runs only the three ordinary/focal pairs (33 calls); `--phase repeated` runs the 50-condition schedule (500 calls). The default `all` runs stress first and then repeated conditions, totaling 533 logical calls before retries. No extra smoke run is added. Each fresh invocation creates a new batch; do not invoke again merely to reread results. `--demo-blocks` cannot shorten live experiments.

Each `runs/live/update3_*/` batch contains `manifest.json`, source snapshots, `results.json`, `results.md`, and `ledger_after.json`. The manifest preserves all scheduled slots, including unstarted ones. Individual run folders contain full requests/responses, raw claims, research metrics, and identity/provenance. Focal probes have one new call and no full-network allocation. The report keeps F1–F4, C1, and stress results separate.

For an unchanged campaign stopped specifically by an empty HTTP 404, with attempts remaining:

```bash
.venv/bin/python diagnostics.py --live --env-file .env --continue-batch runs/live/update3_BATCH_ID
```

This checks model access and saved source/settings/slot identity, preserves accepted outputs, and appends the next attempt. It rejects completed campaigns, arbitrary crash recovery, changed inputs, and unrelated failures. The shared $1 spending guard and unknown-cost reservations remain in force. Demo results never establish model behavior. See the [Stage 03 report](docs/reports/2026-10-14-stage-03-format-communication.md) for the completed execution and findings.

New diagnostic batches snapshot `docs/methods.md` under the same relative path inside the batch. Historical batches retain their original files and source hashes. Changed code or methods still require a new batch under the existing continuation policy.
