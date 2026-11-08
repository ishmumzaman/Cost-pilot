#!/usr/bin/env python3
"""Two fixed diagnostic runs requested in the professor's September 9 feedback."""
import argparse
import fcntl
import hashlib
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pilot

SCHEDULE = ("local_need", "hidden_count")
BASELINE_BATCH = "batch_20260909T043530_41863619"


def analyze(summary, fixture, budget):
    """Descriptive diagnostics only: counties within a run are not independent trials."""
    deaths = {c["id"]: c["overdose_deaths"] for c in fixture["counties"]}
    result = {}
    for round_id in ("1", "2"):
        claims = summary["rounds"][round_id]["claims"]
        percentages = {a: Fraction(v["claim_amount"]) * 100 / Fraction(pilot.number(budget)) for a, v in claims.items()}
        complete = set(claims) == set(pilot.IDS)
        pairs = [(a, b) for a in pilot.IDS for b in pilot.IDS if a in claims and b in claims and deaths[a] < deaths[b]]
        differences = [percentages[b]-percentages[a] for a,b in pairs]
        result[round_id] = {
            "claim_percent_of_budget": {a: pilot.numeric_display(v) for a,v in percentages.items()},
            "total_claim_percent": pilot.numeric_display(sum(percentages.values())) if complete else None,
            "observed_claim_count": len(claims),
            "noninteger_percent_count": sum(v.denominator != 1 for v in percentages.values()),
            "death_order_pairs": len(pairs) if complete else None,
            "concordant_death_pairs": sum(v > 0 for v in differences) if complete else None,
            "tied_death_pairs": sum(v == 0 for v in differences) if complete else None,
            "discordant_death_pairs": sum(v < 0 for v in differences) if complete else None,
        }
    return result


def write_results(folder, config, fixture, runs, stop, simulated):
    report = {
        "simulated": simulated, "schedule": list(SCHEDULE), "planned_runs": 2,
        "started_runs": len(runs), "completed_runs": sum(s["run_status"] == "completed" for s in runs),
        "not_started_runs": len(SCHEDULE)-len(runs), "stop_reason": stop,
        "operational_totals_only": pilot.batch_stats(runs),
        "runs": [{"run_id": s["run_id"], "protocol": s["protocol"], "summary": s,
                  "diagnostics": analyze(s, fixture, config["allocation_budget_usd"])} for s in runs],
    }
    # No mixed-protocol cost projection or model-effect estimate.
    report["operational_totals_only"].pop("projections_usd", None)
    pilot.write_json(folder / "results.json", report)
    lines = ["# Update 2 diagnostic results", "", "SIMULATED DEMO; not live evidence." if simulated else "Live API diagnostics.",
             "", "One fixed attempt per variant, with no replacement of failures. No pooled treatment inference.",
             "", f"Started {len(runs)} / 2; completed {report['completed_runs']}. Stop: {stop or 'none'}.",
             "", "| Protocol | Run | Status | Calls | Cost USD | Monotonic / UTC seconds | Unallocated USD |",
             "|---|---|---|---:|---:|---|---:|"]
    for s in runs:
        unallocated = str(Decimal(s['unallocated_cents'])/100) if s['unallocated_cents'] is not None else "unknown"
        lines.append(f"| {s['protocol']} | [{s['run_id']}](../{s['run_id']}/summary.json) | {s['run_status']} | "
                     f"{s['total_api_attempts']} | {s['estimated_cost_usd'] or 'unknown'} | "
                     f"{s['wall_clock_seconds']:.3f} / {s['utc_elapsed_seconds']:.3f} | {unallocated} |")
    for s in runs:
        lines += ["", f"## {s['protocol']}: requested budget percentages", "",
                  "| County | Round 1 % | Round 2 % | Allocation % |", "|---|---:|---:|---:|"]
        d = analyze(s, fixture, config['allocation_budget_usd'])
        for a in pilot.IDS:
            allocation = pilot.numeric_display(Fraction(s['allocation_cents'][a]) / Fraction(pilot.number(config['allocation_budget_usd']))) if s['allocation_cents'] is not None else "unknown"
            lines.append(f"| {a} | {d['1']['claim_percent_of_budget'].get(a, 'unknown')} | {d['2']['claim_percent_of_budget'].get(a, 'unknown')} | {allocation} |")
    lines += ["", "The local cost is a hypothetical $10,000 per recorded death, not a clinical estimate. Both variants request percentages. The count-omission variant still exposes county/neighbor labels; it cannot guarantee the model will not infer the count. Fixed profiles on one ring cannot isolate network-position effects."]
    (folder / "results.md").write_text("\n".join(lines) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--demo", action="store_true")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--continue-batch", type=Path, help="Explicitly continue an unchanged batch stopped by an empty HTTP 404 after verifying model access")
    args = parser.parse_args(argv)
    config = pilot.load_json((pilot.BASE / "config.json").read_text())
    # This runner has exactly two scheduled variants; no baseline smoke or measured batch.
    config["measured_runs"] = 1
    fixture = pilot.load_json((pilot.BASE / "counties.json").read_text())
    pilot.validate_inputs(config, fixture)
    if args.env_file:
        from dotenv import load_dotenv
        if not args.env_file.is_file():
            parser.error("The specified environment file does not exist")
        load_dotenv(args.env_file, override=False)
    secret = os.environ.get("OPENAI_API_KEY", "") if args.live else ""
    if args.live and not secret:
        parser.error("OPENAI_API_KEY is missing; no API requests were sent")
    root = pilot.BASE / "runs" / ("live" if args.live else "demo")
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Another pilot is using this output directory; wait for it to finish")
        guard = pilot.SpendGuard(root, config["api_spend_limit_usd"])
        provider = pilot.OpenAIProvider(config, secret) if args.live else pilot.DemoProvider()
        if args.continue_batch:
            try:
                folder = args.continue_batch.resolve()
                if folder.parent != root.resolve():
                    raise ValueError("Continuation batch must be in this mode's output directory")
                manifest = pilot.load_json((folder / "manifest.json").read_text())
                prior = pilot.load_json((folder / "results.json").read_text())
                if manifest['settings'] != config or manifest['schedule'] != list(SCHEDULE) or prior['simulated'] != args.demo:
                    raise ValueError("Continuation settings differ from the saved batch")
                runs = [r['summary'] for r in prior['runs']]
                if not runs or runs[-1]['run_status'] != 'incomplete':
                    raise ValueError("No incomplete diagnostic to continue")
                if args.live:
                    model = provider.client.models.retrieve(config['model'])
                    if model.id != config['model']:
                        raise ValueError("Model-access check returned a different identifier")
                tag = uuid.uuid4().hex[:8]
                for name in ('results.json', 'results.md', 'ledger_after.json'):
                    (folder / ("before_continuation_" + tag + "_" + name)).write_bytes((folder/name).read_bytes())
                source = Path(__file__).read_bytes()
                (folder / ("followup_continuation_" + tag + ".py")).write_bytes(source)
                stop = None
                try:
                    last = runs[-1]
                    print("Continuing saved diagnostic:", last['protocol'], flush=True)
                    runs[-1] = pilot.run_once(config, fixture, provider, root, 'diagnostic', guard,
                                             simulated=args.demo, secret=secret, protocol=last['protocol'], resume_from=last['run_id'])
                    if runs[-1]['fatal_batch_error'] or runs[-1]['run_status'] == 'interrupted':
                        stop = runs[-1]['failure_reason']
                    else:
                        for protocol in SCHEDULE[len(runs):]:
                            print("Starting diagnostic:", protocol, flush=True)
                            s = pilot.run_once(config, fixture, provider, root, 'diagnostic', guard,
                                               simulated=args.demo, secret=secret, protocol=protocol)
                            runs.append(s)
                            if s['fatal_batch_error'] or s['run_status'] == 'interrupted':
                                stop = s['failure_reason']
                                break
                except KeyboardInterrupt:
                    stop = 'keyboard_interrupt_between_runs'
                finally:
                    write_results(folder, config, fixture, runs, stop, args.demo)
                    pilot.write_json(folder / 'ledger_after.json', guard.data)
                print("Results:", folder / "results.md")
                return 0 if len(runs) == 2 and all(s['run_status'] == 'completed' for s in runs) else 1
            finally:
                if hasattr(provider, 'close'):
                    provider.close()
        folder = root / ("update2_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:8])
        folder.mkdir()
        source = Path(__file__).read_bytes()
        (folder / "followup_source.py").write_bytes(source)
        (folder / "requirements.txt").write_bytes((pilot.BASE / "requirements.txt").read_bytes())
        pilot.write_json(folder / "manifest.json", {"created_at_utc": pilot.utc(), "settings": config,
                         "schedule": list(SCHEDULE), "runs_per_variant": 1, "replacement_runs": False,
                         "protocols": {k: pilot.PROTOCOLS[k] for k in SCHEDULE}, "allocator_version": pilot.ALLOCATOR_VERSION,
                         "baseline_batch": BASELINE_BATCH, "source_sha256": hashlib.sha256(source).hexdigest(),
                         "source_file": "followup_source.py", "ledger_before": guard.data})
        runs, stop = [], None
        try:
            for protocol in SCHEDULE:
                print("Starting diagnostic:", protocol, "(SIMULATED)" if args.demo else "", flush=True)
                s = pilot.run_once(config, fixture, provider, root, "diagnostic", guard,
                                   simulated=args.demo, secret=secret, protocol=protocol)
                runs.append(s)
                write_results(folder, config, fixture, runs, stop, args.demo)
                print(f"  {s['run_status']}; {s['total_api_attempts']} calls; ${s['estimated_cost_usd'] or 'unknown'}", flush=True)
                if s['fatal_batch_error'] or s['run_status'] == 'interrupted':
                    stop = s['failure_reason']
                    break
        except KeyboardInterrupt:
            stop = "keyboard_interrupt_between_runs"
        finally:
            write_results(folder, config, fixture, runs, stop, args.demo)
            pilot.write_json(folder / "ledger_after.json", guard.data)
            if hasattr(provider, 'close'):
                provider.close()
        print("Results:", folder / "results.md")
        return 0 if len(runs) == 2 and all(s['run_status'] == 'completed' for s in runs) else 1


if __name__ == '__main__':
    sys.exit(main())
