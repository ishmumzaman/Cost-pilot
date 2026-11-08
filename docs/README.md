# Cost Pilot documentation

**Last organized:** 2026-11-08.  
**Current research status:** Stage 03 is complete. Professor Wayne's 2026-10-17 feedback defines the next work; that new experimental stage has not been implemented or run.  
**Start here:** Use this page for the research timeline and next steps. Use the [project README](../README.md) for setup, executable commands, and artifact formats.

## Timeline

Dates refer to the event documented: experiment execution for reports, preparation for plans, and send/receive date for correspondence. A document's later editing date belongs in its header rather than changing its filename on every edit.

| Date | Stage | Document | Status |
|---|---|---|---|
| 2026-09-08 | 01 | [Pilot implementation plan](plans/2026-09-08-stage-01-pilot-implementation.md) | First tracked Git version; includes later amendments |
| 2026-09-09 | 01 | [Live pilot report](reports/2026-09-09-stage-01-pilot-report.md) · [Validation supplement](reports/2026-09-09-stage-01-validation.md) | Complete |
| 2026-09-17 | 02 | [Follow-up diagnostics / Update 2](reports/2026-09-17-stage-02-follow-up-diagnostics.md) | Complete; addresses September 9 feedback |
| 2026-09-23 | 03 | [Need and communication implementation plan](plans/2026-09-23-stage-03-need-communication-implementation.md) | Implemented October 14 |
| 2026-10-14 | 03 | [Format and communication diagnostics / Update 3](reports/2026-10-14-stage-03-format-communication.md) | Complete: 50 repeated runs, three paired probes, 533 accepted outputs |
| 2026-10-17 | 03 | [Sent professor update](updates/2026-10-17-stage-03-email.md) | Summary of sent email shown in the user-provided screenshot |
| 2026-10-17 | 03 → next | [Professor's reply and requested next work](updates/2026-10-17-stage-03-feedback.md) | Received; follow-up pending |

The original historical project context is in [the professor correspondence PDF](reference/original-professor-correspondence.pdf). The current documented executable procedure is in [methods](methods.md). The PDF does not include later messages supplied separately in chat.

## Next research work

The latest [professor feedback](updates/2026-10-17-stage-03-feedback.md) supersedes older plans where their next-step recommendations differ:

1. Write the format effect as a standalone result with estimate-matching and dispersion measurements.
2. Inspect the 16 changed claim pairs and their saved messages, grouped by condition and county, before additional probes.
3. Run approximately 20 ordinary and 20 stronger-message Round 2 requests from each of the three saved states: 120 requests total, with randomized order and a predefined signed change in A's claim as the outcome.
4. Run the percentage-estimate diagnostic on a second model, preferably open-weight. A claim that the format contrast generalizes would additionally need a matched dollar-estimate comparison.
5. Keep the dollar-estimate arm as a comparison; develop subsequent star work around the percentage-estimate arm. Retire the earlier inverse-ordering investigation.

These are recorded requirements, not evidence of completed work. Experimental execution is tracked in the stage report and run manifest.

## Where things belong

- **`updates/`:** Short professor-facing emails, received feedback, and later meeting summaries. Mark each as draft, sent, received, or a summary; do not label a reviewed draft as a verified sent transcript.
- **`reports/`:** Detailed work and results, including what was done, why, how, findings, limitations, and project implications. One primary report per stage; clearly label supporting validation documents.
- **`plans/`:** Proposed implementation scope, acceptance criteria, and completion tracking. Keep completed plans for traceability. Historical plans retain their original scope and should not be treated as the latest instructions.
- **`methods.md`:** The currently documented executable protocol. When a new stage changes methods, date the revision and link its plan/report. Executed runs retain their own frozen source and methods snapshots.
- **`reference/`:** Original background documents, preserving their content. New dated email summaries belong in `updates/`.
- **[`runs/`](../runs/):** Raw prompts, responses, manifests, source snapshots, verification output, and spend ledgers. Link to the existing batch IDs; preserve historical contents and paths.

## Naming and document headers

Use `YYYY-MM-DD-stage-NN-short-topic.md`. Stage numbers connect plans, reports, and correspondence even when their dates differ. Existing Update 2/3 labels remain in report titles and original protocol/run IDs for continuity. Use chronological filenames; archive a document by marking its status or linking its successor rather than moving it to another hierarchy.

Give new documents a short header: **Date**, **Stage**, **Status**, **Source/related feedback**, and **Related report or batch IDs**, as applicable. If the date is uncertain, state that explicitly. The initial plan uses its first tracked Git date; this is not a claim about its original creation time.

Keep email updates concise and link their full reports. Preserve historical observations when adding later corrections; identify the correction and its date. Avoid copying full reports into multiple folders. Correspondence summaries here are summaries, not mailbox exports, and screenshot sources supplied in chat have not been invented as local attachment files.

Commands shown in documents run from the repository root. Markdown links resolve relative to the document containing them. The diagnostics runner snapshots `docs/methods.md` under the same relative path in new batch folders; old batches keep their original layout and source hashes. Reorganization does not make an old batch eligible for continuation after code changes.

## Evidence and backups

`runs/` is Git-ignored. Committing the documentation alone does not preserve the raw evidence. Keep a separate backup of raw live batches and their linked run/source folders, including manifests and verification records; record the actual backup location here when one is established. **No external backup location has been verified during this reorganization.** Keep credentials in the ignored local environment file rather than in documentation or backups of research artifacts.

## Renamed files

This map preserves old references from earlier emails and editor tabs.

| Former root filename | Current location |
|---|---|
| `cost_pilot_implementation_plan.md` | [Stage 01 implementation plan](plans/2026-09-08-stage-01-pilot-implementation.md) |
| `live_test_report.md` | [Stage 01 report](reports/2026-09-09-stage-01-pilot-report.md) |
| `live_validation.md` | [Stage 01 validation](reports/2026-09-09-stage-01-validation.md) |
| `update2.md` | [Stage 02 report](reports/2026-09-17-stage-02-follow-up-diagnostics.md) |
| `need_and_communication_implementation.md` | [Stage 03 implementation plan](plans/2026-09-23-stage-03-need-communication-implementation.md) |
| `update3.md` | [Stage 03 report](reports/2026-10-14-stage-03-format-communication.md) |
| `methods.md` | [Methods](methods.md) |
| `Lehigh University Mail - Inquiry about Undergraduate Research Assistant Positions.pdf` | [Original correspondence PDF](reference/original-professor-correspondence.pdf) |
