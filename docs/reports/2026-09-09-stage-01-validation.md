# Stage 01 — Live pilot validation

**Date:** 2026-09-09 (validation date).  
**Stage:** 01.  
**Status:** Completed validation supplement to the pilot report.  
**Former filename:** `live_validation.md`.

The initial five-county, two-round pilot completed successfully with the planned settings. One development smoke test and five fixed measured attempts produced **60 successful API responses**, with no API failures, retries, rate limits, refusals, truncations, or JSON parse failures. No implementation or prompt changes were needed for this batch.

Evidence: [full batch report](../../runs/live/batch_20260909T043530_41863619/report.md), [machine-readable report](../../runs/live/batch_20260909T043530_41863619/report.json), and [artifact validation](../../runs/live/batch_20260909T043530_41863619/validation.json). Run IDs in the report identify the sibling folders containing complete prompts, responses, configurations, and summaries. These local raw artifacts are intentionally Git-ignored.

| Measurement | Result |
|---|---|
| Measured runs completed | 5 / 5; 50 / 50 API calls |
| Mean run wall time | 15.06 seconds; range 13.24–19.36 |
| Mean input / output tokens per measured run | 3,576.8 / 704.2 |
| Mean estimated cost per measured run | $0.0015604; range $0.0015448–$0.0015760 |
| Five measured runs combined | $0.0078020 |
| Successful development smoke test | $0.0015472 |
| Fresh batch including smoke test | $0.0093492 (less than one cent) |
| Projection for 100 / 1,000 runs with the same configuration | $0.15604 / $1.5604, excluding development |
| Mean raw claims / budget, Round 1 | 1.13; range 1.10–1.14 |
| Mean raw claims / budget, Round 2 | 1.082; range 1.05–1.14 |

Requests used OpenAI Responses, `gpt-5.6-luna`, reasoning `none`, omitted temperature, a 512-token output cap, and sequential execution. All responses returned the same model identifier, temperature `1.0`, and service tier `default`. The API did not expose a separate dated model snapshot; the exact returned identifier and timestamps are saved. The [official pricing](https://developers.openai.com/api/docs/models/gpt-5.6-luna) was rechecked September 9 and matched the saved September 8 snapshot: $0.20 ordinary input, $0.02 cache reads, $0.25 cache writes, and $1.20 output per million tokens. Costs are estimates from reported usage, not a reconciled provider invoice.

Independent inspection of all 60 saved responses verified correct county profiles, only the permitted neighbors' previous-round records, completion of Round 1 before Round 2 began, request settings, token/cost arithmetic, raw claim ratios, and exact proportional allocation. Every allocation was nonnegative and summed to **$10,000,000.00**. The configured credential was absent from the saved run artifacts, and the spending ledger reconciled with the call logs.

Claims overshot the budget in both rounds of every measured run. The average overshoot fell from 13% to 8.2%; this is a descriptive observation from five runs, not evidence of a causal communication effect. Proportional normalization handled the overshoot without changing the raw claims. Numeric claims and valid JSON do not by themselves validate the agents' substantive public-health reasoning.

An [earlier interrupted development attempt](../../runs/live/batch_20260909T043335_3b06e868/report.md) remains separate: two successful responses cost an estimated $0.0002580, and one interrupted request has unknown usage/outcome. Across all saved live attempts, known estimated spend is **$0.0096072**, with **$0.01 still reserved** for that unknown request. The reservation is an allowance, not an observed charge. The existing $1 local spending guard remains in force; the account's exact remaining balance was not independently checked.

The implementation and initial cost measurement are ready for Professor Wayne's review. The sample does not establish rare-failure rates, concurrent throughput, fairness, or network-position effects. A larger network or changed model/settings needs a separate measurement. The literature and Pennsylvania-table follow-ups remain listed in the implementation plan.
