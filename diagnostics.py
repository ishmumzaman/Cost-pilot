#!/usr/bin/env python3
"""Fixed Update 3 study. Demo is offline; live execution requires --live."""
import argparse
import copy
import fcntl
import hashlib
import os
import random
import sys
import uuid
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pilot

CONDITIONS = {"F1": {"protocol": "baseline", "role": "factorial"},
              "F2": {"protocol": "percentage_only", "role": "factorial"},
              "F3": {"protocol": "local_need_usd", "role": "factorial"},
              "F4": {"protocol": "local_need", "role": "factorial"},
              "C1": {"protocol": "hidden_count", "role": "reference"}}
SOURCES = ("pilot.py", "diagnostics.py", "diagnostics_config.json", "requirements.txt", "docs/methods.md")


def validate_design(design):
    if set(design) != {"runs_per_condition", "scheduling_seed", "stress_pairs", "stress_suffix", "simple_multiples", "conditions"}:
        raise ValueError("Unexpected experiment settings")
    if design["conditions"] != CONDITIONS or design["simple_multiples"] != list(pilot.SIMPLE_MULTIPLES):
        raise ValueError("Conditions or metric definitions differ from the fixed study")
    if type(design["runs_per_condition"]) is not int or not 1 <= design["runs_per_condition"] <= 10:
        raise ValueError("Expected 1 to 10 blocks")
    if design["stress_pairs"] != 3 or type(design["scheduling_seed"]) is not int:
        raise ValueError("Expected three stress pairs and an integer scheduling seed")
    if not isinstance(design["stress_suffix"], str) or not design["stress_suffix"].strip():
        raise ValueError("Missing fixed stress suffix")


def schedule(design, phase="all"):
    validate_design(design)
    if phase not in ("all", "stress", "repeated"):
        raise ValueError("Unknown phase")
    slots = []
    if phase in ("all", "stress"):
        for pair in range(1, design["stress_pairs"]+1):
            for arm in ("stress_parent", "stress_focal"):
                slots.append({"slot_id": f"S{pair}_{arm}", "role": arm, "pair": pair,
                              "condition": None, "block": None, "protocol": "baseline"})
    rng = random.Random(design["scheduling_seed"])
    if phase in ("all", "repeated"):
        for block in range(1, design["runs_per_condition"]+1):
            cells = list(CONDITIONS)
            rng.shuffle(cells)
            for cell in cells:
                slots.append({"slot_id": f"B{block:02d}_{cell}", "condition": cell, "block": block,
                              "pair": None, **CONDITIONS[cell]})
    return [{**s, "status": "unstarted", "run_id": None} for s in slots]


def identity(manifest, slot):
    return {"batch_id": manifest["batch_id"], **{k: slot[k] for k in
            ("slot_id", "role", "condition", "block", "pair", "protocol")}}


def read_summary(root, slot):
    if slot["run_id"] is None:
        return None
    path = root / slot["run_id"] / "summary.json"
    return pilot.load_json(path.read_text()) if path.exists() else None


def focal_state(parent, suffix):
    first = parent["rounds"]["1"]["claims"]
    if set(first) != set(pilot.IDS) or "A" not in parent["rounds"]["2"]["claims"]:
        return None
    return {"parent_run_id": parent["run_id"], "original_round1": first, "suffix": suffix}


def create_batch(root, config, fixture, design, phase, simulated, guard):
    batch_id = "update3_" + pilot.utc().replace("-", "").replace(":", "").split(".")[0] + "_" + uuid.uuid4().hex[:8]
    folder = root / batch_id
    folder.mkdir()
    hashes = {}
    for name in SOURCES:
        data = (pilot.BASE / name).read_bytes()
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    manifest = {"batch_id": batch_id, "created_at_utc": pilot.utc(), "simulated": simulated,
                "settings": config, "fixture": fixture, "design": design, "phase": phase,
                "protocols": copy.deepcopy(pilot.PROTOCOLS), "allocator_version": pilot.ALLOCATOR_VERSION,
                "system": pilot.SYSTEM, "template": pilot.TEMPLATE, "source_hashes": hashes,
                "ledger_before": copy.deepcopy(guard.data), "slots": schedule(design, phase),
                "stop_reason": None, "model_access_checks": [], "continuations": []}
    pilot.write_json(folder / "manifest.json", manifest)
    return folder, manifest


def validate_continuation(root, folder, manifest, config, fixture, design, simulated):
    if folder.resolve().parent != root.resolve() or folder.name != manifest["batch_id"]:
        raise ValueError("Batch must be a direct child of this mode's output directory")
    if (manifest["settings"] != config or manifest["fixture"] != fixture or manifest["design"] != design
            or manifest["simulated"] != simulated or manifest["protocols"] != pilot.PROTOCOLS
            or manifest["allocator_version"] != pilot.ALLOCATOR_VERSION):
        raise ValueError("Saved experiment inputs differ")
    for name, digest in manifest["source_hashes"].items():
        if hashlib.sha256((pilot.BASE / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Source changed; start a versioned batch rather than pool implementations")
    expected = schedule(design, manifest["phase"])
    if len(expected) != len(manifest["slots"]):
        raise ValueError("Schedule length differs")
    seen = set()
    started = []
    encountered_unstarted = False
    for slot, original in zip(manifest["slots"], expected):
        if any(slot[k] != original[k] for k in original if k not in ("status", "run_id")):
            raise ValueError("Schedule identity differs")
        if slot["status"] == "unstarted":
            if slot["run_id"] is not None:
                raise ValueError("Unstarted slot has a run")
            encountered_unstarted = True
            continue
        if encountered_unstarted or slot["status"] in ("running", "interrupted", "interrupted_unknown"):
            raise ValueError("Interrupted or out-of-order slot needs manual reconciliation; no automatic replay")
        if slot["run_id"]:
            if slot["run_id"] in seen or (root/slot["run_id"]).resolve().parent != root.resolve():
                raise ValueError("Invalid or duplicate run ID")
            seen.add(slot["run_id"])
            summary = read_summary(root, slot)
            if summary is None or summary.get("experiment_identity") != identity(manifest, slot):
                raise ValueError("Saved run identity mismatch")
            started.append(slot)
    if not started or started[-1]["status"] != "incomplete":
        raise ValueError("No stopped diagnostic eligible for continuation")
    target = started[-1]
    records = read_calls(root, target)
    last = records[-1] if records else {}
    if (last.get("http_status") != 404 or last.get("raw_response") != {"unparsed_error": ""}
            or last.get("attempt", 99) >= config["max_attempts"]):
        raise ValueError("Only the existing empty-404 rule permits continuation")
    return target["slot_id"]


def read_calls(root, slot):
    if slot["run_id"] is None:
        return []
    path = root / slot["run_id"] / "calls.jsonl"
    return [pilot.load_json(line) for line in path.read_text().splitlines()] if path.exists() else []


def execute_batch(root, folder, manifest, provider, guard, secret="", continue_slot=None):
    config, fixture = manifest["settings"], manifest["fixture"]
    manifest["stop_reason"] = None
    try:
        for slot in manifest["slots"]:
            resume = slot["slot_id"] == continue_slot
            if slot["status"] != "unstarted" and not resume:
                continue
            focal = None
            if slot["role"] == "stress_focal":
                parent_slot = next(s for s in manifest["slots"] if s["pair"] == slot["pair"] and s["role"] == "stress_parent")
                parent = read_summary(root, parent_slot)
                focal = focal_state(parent, manifest["design"]["stress_suffix"]) if parent else None
                if focal is None:
                    slot.update(status="unavailable", reason="missing_parent_round1_or_natural_A_round2")
                    pilot.write_json(folder/"manifest.json", manifest)
                    continue
            if not resume:
                slot["run_id"] = manifest["batch_id"] + "_" + slot["slot_id"]
            slot["status"] = "running"
            pilot.write_json(folder/"manifest.json", manifest)  # Slot is durable BEFORE dispatch.
            print("Starting", slot["slot_id"], "(SIMULATED)" if manifest["simulated"] else "", flush=True)
            summary = pilot.run_once(config, fixture, provider, root, "diagnostic", guard,
                                     simulated=manifest["simulated"], secret=secret, protocol=slot["protocol"],
                                     resume_from=slot["run_id"] if resume else None,
                                     assigned_run_id=slot["run_id"], identity=identity(manifest, slot), focal=focal)
            slot["status"] = summary["run_status"]
            if summary["fatal_batch_error"] or summary["run_status"] == "interrupted":
                manifest["stop_reason"] = summary["failure_reason"]
            pilot.write_json(folder/"manifest.json", manifest)
            write_results(root, folder, manifest, guard)
            print(" ", summary["run_status"], summary["completed_logical_calls"], "/", summary["planned_logical_calls"], "accepted calls", flush=True)
            if manifest["stop_reason"]:
                break
    except KeyboardInterrupt:
        manifest["stop_reason"] = "keyboard_interrupt_between_runs"
    except Exception as exc:
        manifest["stop_reason"] = "implementation_error_" + type(exc).__name__
        raise
    finally:
        for slot in manifest["slots"]:
            if slot["status"] == "running":
                slot["status"] = "interrupted_unknown"
        pilot.write_json(folder/"manifest.json", manifest)
        write_results(root, folder, manifest, guard)


def summarize_conditions(runs, slots):
    output = {}
    for cell in CONDITIONS:
        selected = [r for r in runs if r["identity"]["condition"] == cell]
        output[cell] = {"slots": dict(Counter(s["status"] for s in slots if s["condition"] == cell)), "rounds": {}}
        for round_id in ("1", "2"):
            metrics = [r["summary"]["research_metrics"]["rounds"][round_id] for r in selected]
            complete = [m for m in metrics if m["dispersion_pp"] is not None]
            output[cell]["rounds"][round_id] = {
                "complete_rounds": len(complete),
                "mean_claim_percent_by_agent": {a: pilot.stat([Decimal(m["agents"][a]["claim_percent_of_budget"]) for m in metrics if m["agents"][a]["claim_percent_of_budget"] is not None]) for a in pilot.IDS},
                "raw_sd_pp": pilot.stat([Decimal(m["dispersion_pp"]["population_sd"]) for m in complete]),
                "raw_range_pp": pilot.stat([Decimal(m["dispersion_pp"]["range"]) for m in complete]),
                "exact_matches": sum(m["exact_match_count"] for m in metrics),
                "compliance_denominator": sum(m["compliance_denominator"] for m in metrics),
                "nonwhole_percent_claims": sum(m["nonwhole_percent_count"] for m in metrics),
                "valid_claims": sum(m["observed_claim_count"] for m in metrics),
                "simple_multiple_counts": {n: sum(m["simple_multiple_counts"][n] for m in metrics) for n in pilot.SIMPLE_MULTIPLES},
                "nonincreasing_rounds": {field: sum(m["ordering"][field]["nonincreasing"] is True for m in complete)
                                         for field in ("population", "overdose_deaths", "death_rate_per_100k")}}
        changes = [r["summary"]["research_metrics"] for r in selected]
        output[cell].update(paired_claims=sum(m["paired_count"] for m in changes),
                            unchanged_claims=sum(m["unchanged_count"] for m in changes),
                            mean_absolute_change_pp=pilot.stat([Decimal(m["mean_absolute_change_pp"]) for m in changes if m["mean_absolute_change_pp"] is not None]),
                            budget_classifications=dict(Counter(m["budget_classification"] or "unavailable" for m in changes)),
                            allocated_sd_pp=pilot.stat([Decimal(m["allocation_dispersion_pp"]["population_sd"]) for m in changes if m["allocation_dispersion_pp"] is not None]))
    return output


def stress_results(runs, budget):
    results = []
    for parent in (r for r in runs if r["identity"]["role"] == "stress_parent"):
        pair = parent["identity"]["pair"]
        focal = next((r for r in runs if r["identity"]["pair"] == pair and r["identity"]["role"] == "stress_focal"), None)
        p = parent["summary"]; f = focal["summary"] if focal else None
        normal = p["rounds"]["2"]["claims"].get("A")
        alternative = f["rounds"]["2"]["claims"].get("A") if f else None
        row = {"pair": pair, "parent_run_id": p["run_id"], "focal_run_id": f["run_id"] if f else None,
               "status": "missing", "difference_pp": None, "absolute_difference_pp": None}
        if normal and alternative:
            delta = (Fraction(alternative["claim_amount"])-Fraction(normal["claim_amount"]))*100/Fraction(budget)
            original = f["focal"]["original_round1"]["E"]["message"]
            row.update(status="changed" if delta else "unchanged", difference_pp=pilot.numeric_display(delta),
                       absolute_difference_pp=pilot.numeric_display(abs(delta)),
                       round1_claim_usd=p["rounds"]["1"]["claims"]["A"]["claim_amount"],
                       ordinary_claim_usd=normal["claim_amount"], stress_claim_usd=alternative["claim_amount"],
                       original_message=original, suffix=f["focal"]["suffix"],
                       combined_message=original+" "+f["focal"]["suffix"],
                       suffix_provenance="experimenter_authored", combined_provenance="experimenter_modified")
        results.append(row)
    return results


def contrasts(conditions):
    result = {}
    for left, right in (("F2", "F1"), ("F3", "F1"), ("F4", "F2"), ("F4", "F3"), ("C1", "F2")):
        result[left+"_minus_"+right] = {}
        for r in ("1", "2"):
            a, b = conditions[left]["rounds"][r], conditions[right]["rounds"][r]
            result[left+"_minus_"+right][r] = {
                "claim_percent_by_agent": {county: str(a["mean_claim_percent_by_agent"][county]["mean"]-b["mean_claim_percent_by_agent"][county]["mean"])
                    if a["mean_claim_percent_by_agent"][county] and b["mean_claim_percent_by_agent"][county] else None for county in pilot.IDS},
                "mean_raw_sd_difference_pp": str(a["raw_sd_pp"]["mean"]-b["raw_sd_pp"]["mean"]) if a["raw_sd_pp"] and b["raw_sd_pp"] else None}
    return result


def write_results(root, folder, manifest, guard):
    runs, records = [], []
    for slot in manifest["slots"]:
        summary = read_summary(root, slot)
        if summary and "research_metrics" in summary:
            runs.append({"identity": identity(manifest, slot), "summary": summary})
        records.extend(read_calls(root, slot))
    conditions = summarize_conditions(runs, manifest["slots"])
    result = {"batch_id": manifest["batch_id"], "simulated": manifest["simulated"], "stop_reason": manifest["stop_reason"],
              "slot_status_counts": dict(Counter(s["status"] for s in manifest["slots"])),
              "planned_logical_calls": sum(1 if s["role"] == "stress_focal" else 10 for s in manifest["slots"]),
              "operational_totals_only": pilot.summarize_attempts(records), "conditions": conditions,
              "contrasts": contrasts(conditions), "stress_pairs": stress_results(runs, manifest["settings"]["allocation_budget_usd"]),
              "runs": runs, "ledger_after": copy.deepcopy(guard.data)}
    pilot.write_json(folder/"results.json", result)
    pilot.write_json(folder/"ledger_after.json", guard.data)
    write_markdown(folder, result)
    return result


def fmt(value):
    return "unavailable" if value is None else format(Decimal(str(value)), ".5f").rstrip("0").rstrip(".") or "0"


def write_markdown(folder, result):
    totals = result["operational_totals_only"]
    lines = ["# Update 3 diagnostic results", "", "SIMULATED — not live evidence." if result["simulated"] else "Live diagnostics; exploratory descriptive comparisons.", "",
             f"Batch: `{result['batch_id']}`. Stop reason: {result['stop_reason'] or 'none'}.",
             f"Slot statuses: {result['slot_status_counts']}. Planned logical calls: {result['planned_logical_calls']}.",
             f"Response attempts: {totals['total_api_attempts']}; retries: {totals['retry_count']}; API failures: {totals['api_failed_attempts']}; unusable responses: {totals['unusable_response_count']}.",
             f"Known estimated cost: ${totals['known_usage_cost_usd']}; cost coverage complete: {totals['cost_complete']}. Unknown-usage attempts: {totals['unknown_usage_attempts']}.", "",
             "## Conditions", "", "Means below use runs as replicates. SD is across the five raw claims in each run, in percentage points. Round-specific denominators are retained.", "",
             "| Condition | Round | Complete rounds | Mean claims A / B / C / D / E (%) | Mean raw SD | Exact matches / eligible | Nonwhole % / valid |", "|---|---|---:|---|---:|---:|---:|"]
    for cell, value in result["conditions"].items():
        for r, m in value["rounds"].items():
            means = " / ".join(fmt(m["mean_claim_percent_by_agent"][a]["mean"]) if m["mean_claim_percent_by_agent"][a] else "NA" for a in pilot.IDS)
            lines.append(f"| {cell} | {r} | {m['complete_rounds']} | {means} | {fmt(m['raw_sd_pp']['mean']) if m['raw_sd_pp'] else 'NA'} | {m['exact_matches']} / {m['compliance_denominator']} | {m['nonwhole_percent_claims']} / {m['valid_claims']} |")
    lines += ["", "| Condition | Paired claims unchanged / observed | Final budget classifications |", "|---|---:|---|"]
    for cell, m in result["conditions"].items():
        lines.append(f"| {cell} | {m['unchanged_claims']} / {m['paired_claims']} | {m['budget_classifications']} |")
    lines += ["", "## Controlled comparisons", "", "Differences of condition means (left minus right); C1/F2 is a separate count-omission reference comparison.", "", "| Comparison | Round | Claim differences A / B / C / D / E (pp) | Raw SD difference (pp) |", "|---|---|---|---|"]
    for comparison, rounds in result["contrasts"].items():
        for r, m in rounds.items():
            lines.append(f"| {comparison} | {r} | {' / '.join(fmt(m['claim_percent_by_agent'][a]) for a in pilot.IDS)} | {fmt(m['mean_raw_sd_difference_pp'])} |")
    lines += ["", "## Communication probes", "", "| Pair | Status | Stress minus ordinary claim (pp) |", "|---|---|---:|"]
    for pair in result["stress_pairs"]:
        lines.append(f"| {pair['pair']} | {pair['status']} | {fmt(pair['difference_pp'])} |")
    lines += ["", "Original messages, suffixes, combined messages, provenance, raw ratios, round-multiple flags, ordering counts, run-level ranges/SDs, timing segments, and attempt records are retained in results.json and individual run folders.", "",
              "## Run evidence", "", "| Slot | Run | Status | Calls | Active seconds | UTC span seconds |", "|---|---|---|---:|---:|---:|"]
    for run in result["runs"]:
        s = run["summary"]
        lines.append(f"| {run['identity']['slot_id']} | [{s['run_id']}](../{s['run_id']}/summary.json) | {s['run_status']} | {s['total_api_attempts']} | {s['wall_clock_seconds']:.3f} | {s['utc_elapsed_seconds']:.3f} |")
    lines += ["", "## Limits and next step", "", "No failed run is replaced. Counties within a run are not independent replicates. Local estimates are synthetic information, not empirical intervention costs. Exact multiples are diagnostic flags, not proof of arithmetic errors. Count omission may still permit inference. Stress probes change wording and length, use ordinary-first order, and cannot establish a pure persuasion effect or prove communication never matters. Star experiments remain deferred pending review of responsiveness; star position and incoming message count vary together."]
    (folder/"results.md").write_text("\n".join(lines)+"\n")


def check_access(provider, config, manifest, folder, simulated):
    check = {"checked_at_utc": pilot.utc(), "model": config["model"], "simulated": simulated}
    try:
        if simulated:
            check["status"] = "offline_no_access_check"
        else:
            model = provider.client.models.retrieve(config["model"])
            if model.id != config["model"]:
                raise ValueError("Model-access check returned a different identifier")
            check.update(status="accessible", returned_model=model.id)
        return True
    except Exception as exc:
        check.update(status="failed", error_type=type(exc).__name__, http_status=getattr(exc, "status_code", None))
        manifest["stop_reason"] = "model_access_check_failed"
        return False
    finally:
        manifest["model_access_checks"].append(check)
        pilot.write_json(folder/"manifest.json", manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--phase", choices=("stress", "repeated", "all"), default="all")
    parser.add_argument("--demo-blocks", type=int, default=None)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--continue-batch", type=Path)
    args = parser.parse_args(argv)
    config = pilot.load_json((pilot.BASE/"config.json").read_text())
    fixture = pilot.load_json((pilot.BASE/"counties.json").read_text())
    design = pilot.load_json((pilot.BASE/"diagnostics_config.json").read_text())
    pilot.validate_inputs(config, fixture)
    if args.demo_blocks is not None:
        if not args.demo:
            parser.error("--demo-blocks is only for offline verification")
        design["runs_per_condition"] = args.demo_blocks
    validate_design(design)
    if args.live and design["runs_per_condition"] != 10:
        parser.error("Live design must retain ten scheduled runs per condition")
    if args.env_file:
        from dotenv import load_dotenv
        if not args.env_file.is_file():
            parser.error("Environment file is missing")
        load_dotenv(args.env_file, override=False)
    secret = os.environ.get("OPENAI_API_KEY", "") if args.live else ""
    if args.live and not secret:
        parser.error("OPENAI_API_KEY missing; no API calls sent")
    root = pilot.BASE/"runs"/("demo" if args.demo else "live")
    root.mkdir(parents=True, exist_ok=True)
    with (root/".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Another runner holds the shared output lock")
        guard = pilot.SpendGuard(root, config["api_spend_limit_usd"])
        continue_slot = None
        if args.continue_batch:
            folder = args.continue_batch.resolve()
            manifest = pilot.load_json((folder/"manifest.json").read_text())
            continue_slot = validate_continuation(root, folder, manifest, config, fixture, design, args.demo)
        else:
            folder, manifest = create_batch(root, config, fixture, design, args.phase, args.demo, guard)
        provider = pilot.DemoProvider() if args.demo else pilot.OpenAIProvider(config, secret)
        try:
            if check_access(provider, config, manifest, folder, args.demo):
                if continue_slot:
                    tag = uuid.uuid4().hex[:8]
                    for name in ("results.json", "results.md", "ledger_after.json", "manifest.json"):
                        path = folder/name
                        if path.exists():
                            (folder/("before_continuation_"+tag+"_"+name)).write_bytes(path.read_bytes())
                    manifest["continuations"].append({"slot_id": continue_slot, "at_utc": pilot.utc(), "archive_tag": tag,
                                                       "reason": "explicit continuation after successful access check; empty HTTP 404"})
                execute_batch(root, folder, manifest, provider, guard, secret, continue_slot)
            else:
                write_results(root, folder, manifest, guard)
        finally:
            if hasattr(provider, "close"):
                provider.close()
        print("Results:", folder/"results.md")
        return 0 if all(s["status"] == "completed" for s in manifest["slots"]) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError) as exc:
        print("Diagnostics setup/artifact error:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(2)
