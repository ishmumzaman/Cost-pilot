#!/usr/bin/env python3
"""Five-county, two-round cost pilot. No live calls unless --live is supplied."""
from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from email.utils import parsedate_to_datetime
from fractions import Fraction
from pathlib import Path

BASE = Path(__file__).resolve().parent
IDS = tuple("ABCDE")
EDGES = (("A", "B"), ("B", "C"), ("C", "D"), ("D", "E"), ("E", "A"))
NEIGHBORS = {a: sorted(y if x == a else x for x, y in EDGES if a in (x, y)) for a in IDS}
ALLOCATOR_VERSION = "capped_proportional_largest_remainder_v2"
PROTOCOLS = {
    "percentage_only": {"claim_format": "percent", "show_count": True, "cost_per_death_usd": None},
    "local_need_usd": {"claim_format": "usd", "show_count": True, "cost_per_death_usd": 10000},
    "baseline": {"claim_format": "usd", "show_count": True, "cost_per_death_usd": None},
    "local_need": {"claim_format": "percent", "show_count": True, "cost_per_death_usd": 10000},
    "hidden_count": {"claim_format": "percent", "show_count": False, "cost_per_death_usd": None},
}
SYSTEM = (
    "You are an AI agent representing one county in a discussion about a fixed public-health budget.\n"
    "Your role is to advocate for resources for your county using only the information provided "
    "and the messages you are allowed to see.\nDo not assume access to facts that are not provided.\n"
    "Return only JSON with a finite non-negative numeric claim_amount in USD and a short nonempty message string."
)
TEMPLATE = """County: {county_id}
County data: {own_county_profile}
Number of counties sharing the budget: 5
Your directly connected neighbors: {neighbor_ids}
Total budget across all counties: ${budget}
Round: {round_number} of 2

{round_context}

{round_instruction}
Return a JSON object with exactly these fields:
- claim_amount: your requested amount as a finite non-negative number in USD
- message: your brief justification as a nonempty string"""


def utc():
    return datetime.now(timezone.utc).isoformat()


def reject_constant(value):
    raise ValueError("Non-finite JSON number")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def load_json(text, decimals=False):
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant,
                      **({"parse_float": Decimal, "parse_int": Decimal} if decimals else {}))


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("Expected a numeric value, excluding booleans and strings")
    d = Decimal(str(value))
    if not d.is_finite():
        raise ValueError("Expected a finite number")
    return d


def decimal_string(value):
    """Artifacts use decimal strings for exact money; prompts emit JSON numbers."""
    return str(value)


def dumps(value):
    return json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False, default=decimal_string)


def write_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(dumps(value) + "\n")
    tmp.replace(path)


def sanitize(value, secret):
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, "[REDACTED]")
    if isinstance(value, dict):
        return {k: sanitize(v, secret) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v, secret) for v in value]
    return value


def percent_to_usd(percent, budget):
    percent, budget = number(percent), number(budget)
    with localcontext() as context:
        context.prec = len(percent.as_tuple().digits) + len(budget.as_tuple().digits) + 10
        return percent * budget / 100


def system_prompt(protocol="baseline"):
    if PROTOCOLS[protocol]["claim_format"] == "percent":
        return SYSTEM.replace("claim_amount in USD", "claim_percent as a percentage of the total budget")
    return SYSTEM


def parse_claim(text, protocol="baseline", budget=None):
    field = "claim_percent" if PROTOCOLS[protocol]["claim_format"] == "percent" else "claim_amount"
    obj = load_json(text, decimals=True)
    if not isinstance(obj, dict) or set(obj) != {field, "message"}:
        raise ValueError("Expected exactly " + field + " and message")
    claim = number(obj[field])
    if claim < 0:
        raise ValueError("Negative claim")
    if not isinstance(obj["message"], str) or not obj["message"].strip():
        raise ValueError("Expected a nonempty message string")
    if field == "claim_percent":
        # Preserve the returned percentage; derive dollars without binary-float rounding.
        return {"claim_percent": claim, "claim_amount": percent_to_usd(claim, budget), "message": obj["message"]}
    return {"claim_amount": claim, "message": obj["message"]}


def allocate(claims, budget):
    if set(claims) != set(IDS):
        raise ValueError("Missing or extra county claims")
    values = {a: number(claims[a]) for a in IDS}
    if any(v < 0 for v in values.values()):
        raise ValueError("Negative claim")
    cents = Fraction(number(budget)) * 100
    if cents <= 0 or cents.denominator != 1:
        raise ValueError("Budget must be positive whole cents")
    # Fractions avoid Decimal context rounding for very large or precise valid claims.
    total = sum(map(Fraction, values.values()))
    caps = {a: int(Fraction(v) * 100) for a, v in values.items()}
    if total * 100 <= cents:
        # Pay no more than requested. Unpayable fractions of a cent stay unallocated.
        return caps
    shares = {a: cents * Fraction(v) / total for a, v in values.items()}
    result = {a: v.numerator // v.denominator for a, v in shares.items()}
    order = sorted(IDS, key=lambda a: (-(shares[a] - result[a]), a))
    remaining = int(cents) - sum(result.values())
    # Normally one pass suffices. Sub-cent claim caps can require skipping a county.
    while remaining:
        eligible = [a for a in order if result[a] < caps[a]]
        if not eligible:
            break  # No whole-cent payment fits any remaining claim; retain surplus.
        for a in eligible:
            if not remaining:
                break
            result[a] += 1
            remaining -= 1
    assert all(0 <= result[a] <= caps[a] for a in IDS) and sum(result.values()) <= cents
    return result


def record_text(agent, record, protocol="baseline"):
    # Avoid conversion of arbitrary-precision claims to binary floats or strings in prompts.
    field = "claim_percent" if PROTOCOLS[protocol]["claim_format"] == "percent" else "claim_amount"
    return ('{"agent_id": ' + json.dumps(agent) + ', "' + field + '": ' + str(record[field])
            + ', "message": ' + json.dumps(record["message"], ensure_ascii=True) + '}')


def build_prompt(agent, round_number, counties, budget, previous=None, protocol="baseline"):
    settings = PROTOCOLS[protocol]
    if agent not in IDS or round_number not in (1, 2):
        raise ValueError("Invalid agent or round")
    if round_number == 1:
        context = "No previous messages."
        instruction = "State your requested amount and briefly justify it."
    else:
        if previous is None or set(previous) != set(IDS):
            raise ValueError("Round 2 requires all five Round 1 outputs")
        context = ("Your previous output:\n" + record_text(agent, previous[agent], protocol)
                   + "\nMessages from directly connected counties:\n["
                   + ",\n".join(record_text(n, previous[n], protocol) for n in NEIGHBORS[agent]) + "]")
        instruction = "After considering the available messages, state your final requested amount and briefly justify it."
    profile = {k: v for k, v in counties[agent].items() if k != "id"}
    template = TEMPLATE
    if not settings["show_count"]:
        template = template.replace("Number of counties sharing the budget: 5\n", "")
    if settings["cost_per_death_usd"] is not None:
        local_cost = settings["cost_per_death_usd"] * counties[agent]["overdose_deaths"]
        template = template.replace("Round: {round_number} of 2", (
            "Hypothetical planning estimate for fully funding your own county: "
            f"${local_cost:,}, calculated as ${settings['cost_per_death_usd']:,} per recorded overdose death "
            "times your own county's deaths. This is a synthetic planning assumption, not an empirical intervention cost.\n"
            "Round: {round_number} of 2"))
    if settings["claim_format"] == "percent":
        template = template.replace("claim_amount: your requested amount as a finite non-negative number in USD",
                                    "claim_percent: your requested percentage of the total budget as a finite non-negative number (100 means the entire budget)")
        instruction = instruction.replace("requested amount", "requested percentage of the total budget")
    return template.format(county_id=agent, own_county_profile=json.dumps(profile, sort_keys=True),
                           neighbor_ids=", ".join(NEIGHBORS[agent]), budget=f"{number(budget):,}",
                           round_number=round_number, round_context=context, round_instruction=instruction)


def request_body(config, prompt, protocol="baseline"):
    return {"model": config["model"], "instructions": system_prompt(protocol),
            "input": [{"role": "user", "content": prompt}],
            "reasoning": {"effort": config["reasoning_effort"]},
            "max_output_tokens": config["max_output_tokens"],
            "text": {"format": {"type": "text"}}, "tools": [], "stream": False,
            "service_tier": "default", "store": False}


def validate_inputs(config, fixture):
    expected = {"provider", "model", "reasoning_effort", "max_output_tokens", "temperature",
                "request_timeout_seconds", "max_attempts", "retry_delays_seconds", "max_retry_wait_seconds",
                "allocation_budget_usd", "api_spend_limit_usd", "measured_runs", "pricing"}
    if set(config) != expected:
        raise ValueError("Config has missing or unsupported keys")
    if (config["provider"], config["model"], config["reasoning_effort"], config["temperature"]) != (
            "openai", "gpt-5.6-luna", "none", None):
        raise ValueError("This pilot implements OpenAI Luna, reasoning none, temperature omitted")
    for field, low, high in [("max_output_tokens", 64, 4096), ("max_attempts", 1, 3), ("measured_runs", 1, 100)]:
        v = config[field]
        if type(v) is not int or not low <= v <= high:
            raise ValueError("Invalid " + field)
    for field in ("request_timeout_seconds", "max_retry_wait_seconds"):
        if not 0 < number(config[field]) <= 300:
            raise ValueError("Invalid " + field)
    delays = config["retry_delays_seconds"]
    if not isinstance(delays, list) or len(delays) != 2 or any(not 0 <= number(d) <= 60 for d in delays):
        raise ValueError("Expected two bounded retry delays")
    budget = Fraction(number(config["allocation_budget_usd"])) * 100
    if budget <= 0 or budget.denominator != 1:
        raise ValueError("Funding budget must be positive whole cents")
    if not Decimal(str(config["api_spend_limit_usd"])).is_finite() or Decimal(str(config["api_spend_limit_usd"])) <= 0:
        raise ValueError("Invalid actual API spending limit")
    pricing = config["pricing"]
    if pricing["model"] != config["model"] or not pricing["source"].startswith("https://"):
        raise ValueError("Pricing must match the selected model and have a source")
    datetime.strptime(pricing["checked_date"], "%Y-%m-%d")
    for key in ("ordinary_input_per_million", "cached_input_per_million", "cache_write_per_million", "output_per_million"):
        v = Decimal(str(pricing[key]))
        if not v.is_finite() or v < 0:
            raise ValueError("Invalid price")
    if fixture.get("synthetic") is not True or not fixture.get("definition"):
        raise ValueError("Fixture must be explicitly synthetic with units")
    rows = fixture["counties"]
    if len(rows) != 5 or {r["id"] for r in rows} != set(IDS):
        raise ValueError("Expected exactly counties A through E")
    for row in rows:
        if set(row) != {"id", "population", "overdose_deaths", "death_rate_per_100k", "svi", "poverty_percent", "rural_class"}:
            raise ValueError("Unexpected county profile fields")
        if type(row["population"]) is not int or row["population"] <= 0:
            raise ValueError("Invalid population")
        if type(row["overdose_deaths"]) is not int or row["overdose_deaths"] < 0:
            raise ValueError("Invalid deaths")
        if not 0 <= number(row["svi"]) <= 1 or not 0 <= number(row["poverty_percent"]) <= 100:
            raise ValueError("Invalid county units")
        rate = number(row["death_rate_per_100k"])
        if rate < 0 or abs(rate - Decimal(row["overdose_deaths"]) * 100000 / row["population"]) > Decimal("0.051"):
            raise ValueError("Death rate inconsistent with annual deaths/population")
        if not isinstance(row["rural_class"], str) or not row["rural_class"].strip():
            raise ValueError("Invalid rural class")
    return {r["id"]: r for r in rows}


def usage_cost(usage, pricing, returned_model=None, service_tier=None):
    """Keep known token totals even when billing categories are missing/invalid."""
    result = {"input_tokens": None, "output_tokens": None, "total_tokens": None,
              "usage_complete": False, "estimated_cost_usd": None, "cost_reason": "missing_usage"}
    if not isinstance(usage, dict):
        return result
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        v = usage.get(key)
        if type(v) is int and v >= 0:
            result[key] = v
    i, o, total = (result[k] for k in ("input_tokens", "output_tokens", "total_tokens"))
    if i is None or o is None or total is None or i + o != total:
        result["cost_reason"] = "missing_or_inconsistent_token_totals"
        return result
    result["usage_complete"] = True
    details = usage.get("input_tokens_details") or {}
    read, write = details.get("cached_tokens"), details.get("cache_write_tokens")
    # Luna's cache writes are billable: absent details cannot safely mean zero.
    if any(type(n) is not int or n < 0 for n in (read, write)) or read + write > i:
        result["cost_reason"] = "missing_or_inconsistent_cache_categories"
        return result
    if returned_model != pricing["model"] or service_tier not in (None, "default"):
        result["cost_reason"] = "unverified_model_or_service_tier_pricing"
        return result
    if i > 272000:
        result["cost_reason"] = "outside_short_context_pricing"
        return result
    result["billing_tokens"] = {"ordinary_input": i - read - write, "cached_input": read,
                                "cache_write": write, "output": o}
    cost = sum(Decimal(n) * Decimal(pricing[k + "_per_million"])
               for k, n in result["billing_tokens"].items()) / 1000000
    result.update(estimated_cost_usd=str(cost), cost_reason=None)
    return result


class ApiFailure(Exception):
    def __init__(self, kind, status=None, retry_after=None, body=None, request_id=None):
        super().__init__(kind)
        self.kind, self.status, self.retry_after = kind, status, retry_after
        self.body, self.request_id = body, request_id
        self.transient = kind in ("connection", "timeout") or status in (408, 409, 429) or (status is not None and status >= 500)
        error_body = body.get("error") if isinstance(body, dict) else None
        self.fatal = status in (400, 401, 403, 404, 422) or (status == 429 and isinstance(error_body, dict)
                     and error_body.get("code") == "insufficient_quota")
        if self.fatal:
            self.transient = False


def retry_after_seconds(headers):
    try:
        if headers.get("retry-after-ms") is not None:
            value = float(headers["retry-after-ms"]) / 1000
        else:
            raw = headers.get("retry-after")
            if raw is None:
                return None
            try:
                value = float(raw)
            except ValueError:
                value = (parsedate_to_datetime(raw) - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, value) if math.isfinite(value) else None
    except (ValueError, TypeError, OverflowError):
        return None


class OpenAIProvider:
    def __init__(self, config, api_key):
        import openai
        self.sdk = openai
        self.version = openai.__version__
        self.client = openai.OpenAI(api_key=api_key, base_url="https://api.openai.com/v1",
                                    max_retries=0, timeout=float(config["request_timeout_seconds"]))

    def __call__(self, request):
        try:
            raw = self.client.responses.with_raw_response.create(**request)
            body = raw.http_response.json()
            return {"body": body, "http_status": raw.status_code,
                    "request_id": raw.headers.get("x-request-id")}
        except self.sdk.APIStatusError as exc:
            try:
                body = exc.response.json()
            except ValueError:
                body = {"unparsed_error": exc.response.text}
            raise ApiFailure("api_status", exc.status_code, retry_after_seconds(exc.response.headers),
                             body, exc.response.headers.get("x-request-id")) from None
        except self.sdk.APITimeoutError:
            raise ApiFailure("timeout") from None
        except self.sdk.APIConnectionError:
            raise ApiFailure("connection") from None

    def close(self):
        self.client.close()


class SpendGuard:
    """Small persistent reservation ledger, protected by the CLI's directory lock."""
    def __init__(self, root, limit):
        self.path = root / "spend.json"
        self.limit = Decimal(str(limit))
        self.data = load_json(self.path.read_text()) if self.path.exists() else {"known_cost_usd": "0", "reservations": {}}
        if not isinstance(self.data.get("reservations"), dict):
            raise ValueError("Invalid spend ledger")
        amounts = [self.data["known_cost_usd"]] + list(self.data["reservations"].values())
        if any(not Decimal(v).is_finite() or Decimal(v) < 0 for v in amounts):
            raise ValueError("Invalid spend ledger amounts")

    @property
    def committed(self):
        return Decimal(self.data["known_cost_usd"]) + sum((Decimal(v) for v in self.data["reservations"].values()), Decimal(0))

    def reserve(self, attempt_id, request, config):
        # UTF-8 bytes + allowance for provider framing is deliberately generous for these small prompts.
        upper_input = len(json.dumps(request, ensure_ascii=True).encode()) + 4096
        p = config["pricing"]
        allowance = (Decimal(upper_input) * max(Decimal(p[k]) for k in
                    ("ordinary_input_per_million", "cached_input_per_million", "cache_write_per_million"))
                     + Decimal(config["max_output_tokens"]) * Decimal(p["output_per_million"])) / 1000000
        allowance = max(Decimal("0.01"), allowance)
        if self.committed + allowance > self.limit:
            return False
        self.data["reservations"][attempt_id] = str(allowance)
        write_json(self.path, self.data)
        return True

    def settle(self, attempt_id, cost):
        if cost is not None:
            self.data["reservations"].pop(attempt_id)
            self.data["known_cost_usd"] = str(Decimal(self.data["known_cost_usd"]) + Decimal(cost))
            write_json(self.path, self.data)
        # Unknown usage retains its reservation across restarts; it is never treated as free.


def inspect_response(body, protocol="baseline", budget=None):
    parts, refusals = [], []
    outputs = body.get("output") or []
    unexpected = False
    incomplete_message = False
    for item in outputs:
        if item.get("type") == "message":
            incomplete_message |= item.get("status") not in (None, "completed")
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    parts.append(content.get("text", ""))
                elif content.get("type") == "refusal":
                    refusals.append(content.get("refusal", ""))
                else:
                    unexpected = True
        elif item.get("type") != "reasoning":
            unexpected = True
    text = "".join(parts)
    parsed, parse_error = None, None
    try:
        parsed = parse_claim(text, protocol, budget)
    except (ValueError, InvalidOperation, RecursionError) as exc:
        parse_error = type(exc).__name__ + ": " + str(exc)
    reason = ("refusal" if refusals else "incomplete_response" if body.get("status") != "completed" or incomplete_message
              else "unexpected_output" if unexpected else "parse_failure" if parse_error else None)
    return {"raw_text": text, "parsed_output": parsed, "parse_success": parse_error is None,
            "parse_error": parse_error, "usable": reason is None, "unusable_reason": reason,
            "refusals": refusals, "response_status": body.get("status"),
            "stop_reason": body.get("incomplete_details") or body.get("error")}


def numeric_display(fraction):
    # Display/derived metrics only; claims and allocator retain exact values.
    f = Fraction(fraction)
    return str(Decimal(f.numerator) / Decimal(f.denominator))


def diagnostics(rounds, budget):
    result = {}
    for r, outputs in rounds.items():
        total = sum((Fraction(x["claim_amount"]) for x in outputs.values()), Fraction(0))
        result[r] = {"observed_claim_count": len(outputs), "claims": outputs,
                     "claim_percent_of_budget": {a: numeric_display(Fraction(x["claim_amount"]) * 100 / Fraction(number(budget))) for a, x in outputs.items()},
                     "raw_total_claims_usd": numeric_display(total),
                     "claim_budget_ratio": numeric_display(total / Fraction(number(budget))) if len(outputs) == 5 else None}
    changes = {a: numeric_display(Fraction(rounds["2"][a]["claim_amount"]) - Fraction(rounds["1"][a]["claim_amount"]))
               for a in IDS if a in rounds["1"] and a in rounds["2"]}
    return {"rounds": result, "claim_changes_usd": changes, "paired_claim_count": len(changes),
            "unchanged_claim_count": sum(Decimal(v) == 0 for v in changes.values()),
            "mean_absolute_claim_change_usd": numeric_display(sum((abs(Fraction(v)) for v in changes.values()), Fraction(0)) / len(changes)) if changes else None}


def summarize_attempts(records):
    ids = {r["logical_call_id"] for r in records}
    costs = [Decimal(r["estimated_cost_usd"]) for r in records if r["estimated_cost_usd"] is not None]
    result = {
        "total_api_attempts": len(records), "started_logical_calls": len(ids),
        "retry_count": len(records) - len(ids),
        "api_failed_attempts": sum(r["api_success"] is False for r in records),
        "unknown_outcome_attempts": sum(r["api_success"] is None for r in records),
        "rate_limit_count": sum(r["http_status"] == 429 for r in records),
        "parse_failure_count": sum(r["parse_success"] is False for r in records),
        "parsed_response_count": sum(r["parse_success"] is not None for r in records),
        "unusable_response_count": sum(r["api_success"] is True and not r["usable"] for r in records),
        "usage_complete": all(r["usage_complete"] for r in records),
        "unknown_usage_attempts": sum(not r["usage_complete"] for r in records),
        "cost_complete": len(costs) == len(records),
        "known_usage_cost_usd": str(sum(costs, Decimal(0))),
        "estimated_cost_usd": str(sum(costs, Decimal(0))) if len(costs) == len(records) else None,
    }
    for k in ("input_tokens", "output_tokens", "total_tokens"):
        result["known_" + k] = sum(r[k] for r in records if r[k] is not None)
        result[k] = result["known_" + k] if all(r[k] is not None for r in records) else None
    return result


SIMPLE_MULTIPLES = ("0.01", "0.1", "0.5", "2", "10", "100")


def restore_claims(claims):
    return {a: {**v, "claim_amount": Decimal(str(v["claim_amount"])),
                **({"claim_percent": Decimal(str(v["claim_percent"]))} if "claim_percent" in v else {})}
            for a, v in claims.items()}


def estimate_metrics(claim, estimate):
    result = {"supplied_estimate_usd": None if estimate is None else numeric_display(estimate),
              "claim_to_estimate_ratio": None, "ratio_exact": None, "claim_equals_estimate": None,
              "simple_multiple": None, "estimate_metric_reason": None}
    if estimate is None:
        result["estimate_metric_reason"] = "not_supplied"
    elif claim is None:
        result["estimate_metric_reason"] = "missing_output"
    else:
        claim, estimate = Fraction(claim), Fraction(estimate)
        result["claim_equals_estimate"] = claim == estimate
        if estimate == 0:
            result["estimate_metric_reason"] = "zero_estimate"
        else:
            ratio = claim / estimate
            result.update(claim_to_estimate_ratio=numeric_display(ratio), ratio_exact=str(ratio),
                          simple_multiple=next((v for v in SIMPLE_MULTIPLES if ratio == Fraction(v)), None))
    return result


def dispersion(values):
    values = list(map(Fraction, values))
    if not values:
        return None
    mean = sum(values) / len(values)
    variance = sum((v-mean)**2 for v in values) / len(values)
    return {"mean": numeric_display(mean), "min": numeric_display(min(values)),
            "max": numeric_display(max(values)), "range": numeric_display(max(values)-min(values)),
            "population_sd": str(Decimal(numeric_display(variance)).sqrt())}


def ordering(percentages, counties, field):
    differences = [percentages[b]-percentages[a] for a in IDS for b in IDS
                   if number(counties[a][field]) < number(counties[b][field])]
    return {"ordered_pair_count": len(differences), "increasing": sum(v > 0 for v in differences),
            "equal": sum(v == 0 for v in differences), "decreasing": sum(v < 0 for v in differences),
            "nonincreasing": all(v <= 0 for v in differences) if differences else None}


def research_metrics(rounds, budget, counties, protocol, allocation=None):
    """Exact comparisons; rounded strings are presentation values, never decision inputs."""
    budget = Fraction(number(budget))
    multiplier = PROTOCOLS[protocol]["cost_per_death_usd"]
    result = {"rounds": {}, "claim_changes": {}, "allocation_dispersion_pp": None,
              "budget_classification": None, "allocated_plus_unallocated_equals_budget": None}
    for r in ("1", "2"):
        claims = rounds[r]
        complete = set(claims) == set(IDS)
        percentages = {a: Fraction(v["claim_amount"])*100/budget for a, v in claims.items()}
        agents = {}
        for a in IDS:
            estimate = None if multiplier is None else Fraction(multiplier)*counties[a]["overdose_deaths"]
            agents[a] = {"claim_percent_of_budget": numeric_display(percentages[a]) if a in percentages else None,
                         **estimate_metrics(claims[a]["claim_amount"] if a in claims else None, estimate)}
        eligible = [v for v in agents.values() if v["claim_equals_estimate"] is not None]
        result["rounds"][r] = {
            "agents": agents, "observed_claim_count": len(claims), "missing_output_count": 5-len(claims),
            "exact_match_count": sum(v["claim_equals_estimate"] for v in eligible),
            "compliance_denominator": len(eligible),
            "simple_multiple_counts": {n: sum(v["simple_multiple"] == n for v in agents.values()) for n in SIMPLE_MULTIPLES},
            "nonwhole_percent_count": sum(v.denominator != 1 for v in percentages.values()),
            "dispersion_pp": dispersion(percentages.values()) if complete else None,
            "ordering": {field: ordering(percentages, counties, field) if complete else None
                         for field in ("population", "overdose_deaths", "death_rate_per_100k")},
        }
    exact_changes = []
    for a in IDS:
        if a in rounds["1"] and a in rounds["2"]:
            change = Fraction(rounds["2"][a]["claim_amount"])-Fraction(rounds["1"][a]["claim_amount"])
            exact_changes.append(change*100/budget)
            result["claim_changes"][a] = {"changed": change != 0, "change_pp": numeric_display(change*100/budget)}
    changes = result["claim_changes"]
    result.update(paired_count=len(changes), unchanged_count=sum(not v["changed"] for v in changes.values()),
                  mean_absolute_change_pp=numeric_display(sum(map(abs, exact_changes)) / len(exact_changes)) if changes else None)
    if set(rounds["2"]) == set(IDS):
        total = sum(Fraction(v["claim_amount"]) for v in rounds["2"].values())
        result["budget_classification"] = "under" if total < budget else "over" if total > budget else "equal"
        result["raw_total_claims_usd"] = numeric_display(total)
    if allocation is not None:
        paid = sum(allocation.values())
        surplus = int(budget*100)-paid
        result.update(allocation_dispersion_pp=dispersion(Fraction(v)/budget for v in allocation.values()),
                      allocated_cents=paid, unallocated_cents=surplus,
                      allocated_plus_unallocated_equals_budget=paid+surplus == budget*100)
    return result


def message_exposure(agent, round_number, neighbors=None):
    senders = list((NEIGHBORS if neighbors is None else neighbors)[agent]) if round_number == 2 else []
    return {"neighbor_message_count": len(senders), "neighbor_sender_ids": senders,
            "own_prior_output_supplied": round_number == 2}


def execute_call(config, provider, folder, run_id, agent, round_number, request, protocol,
                 guard, records, summary, identity=None, secret="", sleep=time.sleep, clock=time.monotonic):
    """Single shared transport/retry/logging path for ordinary and focal stress calls."""
    logical = f"{run_id}_r{round_number}_{agent}"
    prior_attempts = [r for r in records if r["logical_call_id"] == logical]
    prior_error = "manual_continuation_after_empty_404" if prior_attempts else None
    wait_before_attempt = 0.0
    for attempt in range(len(prior_attempts) + 1, config["max_attempts"] + 1):
        attempt_id = f"{logical}_a{attempt}"
        if not guard.reserve(attempt_id, request, config):
            summary.update(run_status="interrupted", failure_reason="spending_limit")
            return None
        record = {"run_id": run_id, "agent_id": agent, "round": round_number,
                  "logical_call_id": logical, "attempt_id": attempt_id, "attempt": attempt,
                  "request_started_at_utc": utc(), "request": request,
                  "experiment_identity": identity, **message_exposure(agent, round_number),
                  "requested_model": config["model"], "returned_model": None,
                  "api_success": None, "http_status": None, "provider_request_id": None,
                  "parse_success": None, "usable": False, "retry_reason": prior_error,
                  "retry_wait_before_seconds": wait_before_attempt,
                  "raw_response": None, "error": None, **usage_cost(None, config["pricing"])}
        t0 = clock()
        failure = None
        try:
            reply = provider(request)
            body = reply["body"]
            record.update(api_success=True, http_status=reply["http_status"],
                          provider_request_id=reply["request_id"], raw_response=body,
                          returned_model=body.get("model"), temperature_returned=body.get("temperature"),
                          service_tier_returned=body.get("service_tier"),
                          raw_usage=body.get("usage"))
            record.update(usage_cost(body.get("usage"), config["pricing"], body.get("model"), body.get("service_tier")))
            record.update(inspect_response(body, protocol, config["allocation_budget_usd"]))
        except ApiFailure as exc:
            failure = exc
            record.update(api_success=False, http_status=exc.status, error=exc.kind,
                          provider_request_id=exc.request_id, raw_response=exc.body,
                          retry_after_seconds=exc.retry_after)
            if isinstance(exc.body, dict):
                record["raw_usage"] = exc.body.get("usage")
                record.update(usage_cost(exc.body.get("usage"), config["pricing"], exc.body.get("model")))
        except KeyboardInterrupt:
            record["error"] = "interrupted_request"
            raise
        except Exception as exc:
            record["error"] = "unexpected_" + type(exc).__name__
            raise
        finally:
            record.update(response_received_at_utc=utc(), latency_seconds=clock() - t0)
            record = sanitize(record, secret)
            with (folder / "calls.jsonl").open("a") as f:
                f.write(json.dumps(record, default=decimal_string, ensure_ascii=True, allow_nan=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
            records.append(record)
            guard.settle(attempt_id, record["estimated_cost_usd"])
        if record["usable"]:
            return record["parsed_output"]
        if failure and failure.transient and attempt < config["max_attempts"]:
            wait = max(config["retry_delays_seconds"][attempt-1], failure.retry_after or 0)
            if wait > config["max_retry_wait_seconds"]:
                summary.update(run_status="interrupted", failure_reason="retry_after_exceeds_wait_limit")
                return None
            before_wait = clock()
            try:
                sleep(wait)
            finally:
                wait_before_attempt = clock() - before_wait
                summary["retry_wait_seconds"] += wait_before_attempt
            prior_error = failure.kind
            continue
        summary.update(run_status="incomplete", failure_reason=failure.kind if failure else record["unusable_reason"],
                       fatal_batch_error=bool(failure and failure.fatal))
        break
    return None


def run_once(config, fixture, provider, root, kind, guard, simulated=False, sleep=time.sleep, clock=time.monotonic, secret="", protocol="baseline", resume_from=None, assigned_run_id=None, identity=None, focal=None):
    counties = validate_inputs(config, fixture)
    protocol_settings = PROTOCOLS[protocol]
    # Focal calls replay an external Round 1 state; borrowed outputs are never counted as new calls.
    focal_previous = None
    if focal is not None:
        if protocol != "baseline" or set(focal) != {"parent_run_id", "original_round1", "suffix"}:
            raise ValueError("Invalid baseline focal probe")
        focal_previous = restore_claims(focal["original_round1"])
        if set(focal_previous) != set(IDS) or not isinstance(focal["suffix"], str) or not focal["suffix"].strip():
            raise ValueError("Focal probe requires complete Round 1 and a fixed suffix")
        focal_previous["E"]["message"] += " " + focal["suffix"]
    planned = 1 if focal is not None else 10
    if resume_from is None:
        run_id = assigned_run_id or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + kind + "_" + uuid.uuid4().hex[:10])
        folder = root / run_id
        if folder.resolve().parent != root.resolve():
            raise ValueError("Run must be a direct child folder")
        folder.mkdir()
        started = clock()
        started_utc = utc()
        source = Path(__file__).read_bytes()
        (folder / "pilot_source.py").write_bytes(source)
        try:
            git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=BASE, stderr=subprocess.DEVNULL, text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            git_commit = None
        write_json(folder / "config.json", {"run_id": run_id, "kind": kind, "simulated": simulated,
                   "experiment_identity": identity, "focal": focal,
                   "settings": config, "county_data": fixture, "edges": EDGES, "system_prompt": system_prompt(protocol),
                   "protocol": protocol, "protocol_settings": protocol_settings, "allocator_version": ALLOCATOR_VERSION,
                   "source_sha256": hashlib.sha256(source).hexdigest(), "source_file": "pilot_source.py",
                   "user_template_note": "Baseline template below; full rendered prompts in calls.jsonl include protocol modifications",
                   "user_template": TEMPLATE, "temperature_sent": False, "allocation_rule_disclosed": False,
                   "concurrency": 1, "orchestrator": "plain_python", "started_at_utc": utc(),
                   "python_version": platform.python_version(), "sdk_version": getattr(provider, "version", None),
                   "git_commit": git_commit, "money_encoding": "Decimal strings for claims/costs; integer cents for allocations"})
        records, rounds = [], {"1": {}, "2": {}}
        summary = {"run_id": run_id, "kind": kind, "simulated": simulated, "run_status": "running",
                   "allocation_cents": None, "allocation_status": "unavailable", "unallocated_cents": None, "failure_reason": None,
                   "protocol": protocol, "experiment_identity": identity, "focal": focal, "allocator_version": ALLOCATOR_VERSION,
                   "fatal_batch_error": False, "started_at_utc": started_utc, "planned_logical_calls": planned,
                   "timing_scope": "Whole run through final summary construction; excludes final summary serialization and batch report"}
        if focal is not None:
            summary["focal_provenance"] = {"original_message": focal["original_round1"]["E"]["message"],
                "suffix": focal["suffix"], "combined_message": focal_previous["E"]["message"],
                "suffix_provenance": "experimenter_authored", "combined_provenance": "experimenter_modified",
                "sender": "E", "recipient": "A"}
        write_json(folder / "summary.json", summary)
        summary["retry_wait_seconds"] = 0.0
        prior_wall = 0.0
        segments = []
    else:
        # Explicit, narrowly scoped recovery of the observed empty-404 diagnostic failure.
        folder = root / resume_from
        if folder.resolve().parent != root.resolve():
            raise ValueError("Continuation must use a direct child run folder")
        snapshot = load_json((folder / "config.json").read_text())
        summary = load_json((folder / "summary.json").read_text())
        records = [load_json(line) for line in (folder / "calls.jsonl").read_text().splitlines()]
        last = records[-1] if records else {}
        if (snapshot["settings"] != config or snapshot["county_data"] != fixture
                or snapshot.get("protocol") != protocol or snapshot.get("protocol_settings") != protocol_settings
                or snapshot.get("allocator_version") != ALLOCATOR_VERSION or snapshot["simulated"] != simulated
                or snapshot.get("experiment_identity") != identity or snapshot.get("focal") != focal
                or kind != "diagnostic" or summary["kind"] != kind
                or summary["run_status"] != "incomplete" or last.get("http_status") != 404
                or last.get("raw_response") != {"unparsed_error": ""} or last["attempt"] >= config["max_attempts"]):
            raise ValueError("Only unchanged diagnostic runs stopped by an empty 404 can be continued")
        rounds = {r: {a: {**v, "claim_amount": Decimal(v["claim_amount"]),
                           **({"claim_percent": Decimal(v["claim_percent"])} if "claim_percent" in v else {})}
                       for a, v in summary["rounds"][r]["claims"].items()} for r in ("1", "2")}
        # Verify all logged prompts still match this implementation before making new calls.
        for record in records:
            prompt = build_prompt(record["agent_id"], record["round"], counties, config["allocation_budget_usd"],
                                  (focal_previous if focal is not None else rounds["1"]) if record["round"] == 2 else None, protocol)
            if request_body(config, prompt, protocol) != record["request"]:
                raise ValueError("Continuation would change a saved prompt")
        index = len(summary.get("continuations", [])) + 1
        write_json(folder / f"summary_before_continuation_{index}.json", summary)
        source = Path(__file__).read_bytes()
        source_file = f"pilot_continuation_{index}.py"
        (folder / source_file).write_bytes(source)
        summary.setdefault("continuations", []).append({"reason": "manual continuation after successful model-access check following empty HTTP 404",
                    "source_file": source_file, "source_sha256": hashlib.sha256(source).hexdigest(), "started_at_utc": utc()})
        prior_wall = summary["wall_clock_seconds"]
        segments = summary.get("execution_segments", [{"started_at_utc": summary["started_at_utc"],
                     "finished_at_utc": summary["finished_at_utc"], "monotonic_seconds": prior_wall}])
        started, started_utc = clock(), utc()
        run_id = summary["run_id"]
        summary.update(run_status="running", failure_reason=None, fatal_batch_error=False,
                       timing_scope="Sum of active execution segments; excludes the manual recovery pause and final serialization/reporting")
        write_json(folder / "summary.json", summary)

    try:
        for round_number in ((2,) if focal is not None else (1, 2)):
            previous = copy.deepcopy(focal_previous if focal is not None else rounds["1"]) if round_number == 2 else None
            for agent in (("A",) if focal is not None else IDS):
                if agent in rounds[str(round_number)]:
                    continue
                prompt = build_prompt(agent, round_number, counties, config["allocation_budget_usd"], previous, protocol)
                request = request_body(config, prompt, protocol)
                logical = f"{run_id}_r{round_number}_{agent}"
                parsed = execute_call(config, provider, folder, run_id, agent, round_number,
                                      request, protocol, guard, records, summary, identity,
                                      secret, sleep, clock)
                if parsed is not None:
                    rounds[str(round_number)][agent] = parsed
                if parsed is None:
                    return summary
        if focal is not None:
            summary.update(run_status="completed", allocation_status="not_applicable_focal_probe")
            return summary
        final = {a: r["claim_amount"] for a, r in rounds["2"].items()}
        allocation = allocate(final, config["allocation_budget_usd"])
        surplus = int(Fraction(number(config["allocation_budget_usd"])) * 100) - sum(allocation.values())
        summary.update(allocation_cents=allocation, unallocated_cents=surplus,
                       allocation_status="allocated_with_surplus" if surplus else "allocated", run_status="completed")
    except KeyboardInterrupt:
        summary.update(run_status="interrupted", failure_reason="keyboard_interrupt")
    except Exception as exc:
        summary.update(run_status="incomplete", failure_reason="implementation_error_" + type(exc).__name__, fatal_batch_error=True)
        # Keep credentials or API bodies out of exception text. Full records already preserved.
    finally:
        summary.update(summarize_attempts(records))
        completed = sum(len(v) for v in rounds.values())
        summary.update(completed_logical_calls=completed,
                       failed_logical_calls=len({r["logical_call_id"] for r in records}) - completed,
                       conversation_complete=completed == planned,
                       allocation_sum_cents=sum(summary["allocation_cents"].values()) if summary["allocation_cents"] is not None else None,
                       **diagnostics(rounds, config["allocation_budget_usd"]))
        summary["research_metrics"] = research_metrics(rounds, config["allocation_budget_usd"], counties, protocol, summary["allocation_cents"])
        summary["per_round_usage"] = {str(n): summarize_attempts([r for r in records if r["round"] == n]) for n in (1, 2)}
        segment_seconds, finished = clock()-started, utc()
        segments.append({"started_at_utc": started_utc, "finished_at_utc": finished, "monotonic_seconds": segment_seconds})
        summary.update(wall_clock_seconds=prior_wall+segment_seconds, finished_at_utc=finished, execution_segments=segments)
        summary["active_utc_elapsed_seconds"] = sum((datetime.fromisoformat(v["finished_at_utc"]) - datetime.fromisoformat(v["started_at_utc"])).total_seconds() for v in segments)
        summary["active_utc_minus_monotonic_seconds"] = summary["active_utc_elapsed_seconds"] - summary["wall_clock_seconds"]
        summary["utc_elapsed_seconds"] = (datetime.fromisoformat(summary["finished_at_utc"]) - datetime.fromisoformat(summary["started_at_utc"])).total_seconds()
        summary["utc_minus_monotonic_seconds"] = summary["utc_elapsed_seconds"] - summary["wall_clock_seconds"]
        write_json(folder / "summary.json", summary)
    return summary


class DemoProvider:
    """Deterministic fixture transport, never evidence of LLM behavior/cost/latency."""
    version = "offline-demo"

    def __call__(self, request):
        prompt = request["input"][0]["content"]
        agent = prompt.splitlines()[0].split(": ")[1]
        index = IDS.index(agent)
        claim = 1000000 + index * 300000 + (100000 if "Round: 2 of 2" in prompt else 0)
        value = {"claim_percent": claim / 100000} if "claim_percent:" in prompt else {"claim_amount": claim}
        text = json.dumps({**value, "message": f"SIMULATED fixture statement from County {agent}."})
        return {"http_status": 200, "request_id": "simulated-request",
                "body": {"model": request["model"], "status": "completed", "service_tier": "default",
                         "output": [{"type": "message", "status": "completed", "role": "assistant",
                                     "content": [{"type": "output_text", "text": text}]}],
                         "usage": {"input_tokens": 400, "output_tokens": 50, "total_tokens": 450,
                                   "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0}}}}


def stat(values):
    return {"n": len(values), "mean": statistics.mean(values), "min": min(values), "max": max(values)} if values else None


def batch_stats(runs):
    keys = ("wall_clock_seconds", "input_tokens", "output_tokens", "total_tokens", "estimated_cost_usd")
    result = {k: stat([Decimal(str(r[k])) for r in runs if r[k] is not None]) for k in keys}
    result["started"] = len(runs)
    result["completed"] = sum(r["run_status"] == "completed" for r in runs)
    result["known_cost_usd"] = str(sum((Decimal(r["known_usage_cost_usd"]) for r in runs), Decimal(0)))
    result["cost_complete"] = all(r["cost_complete"] for r in runs)
    result["effective_cost_per_completed_run_usd"] = (str(Decimal(result["known_cost_usd"]) / result["completed"])
                if result["cost_complete"] and result["completed"] else None)
    result["projections_usd"] = ({str(n): str(Decimal(result["known_cost_usd"]) / len(runs) * n) for n in (100,1000)}
                                 if runs and result["cost_complete"] else None)
    result["round_ratios"] = {r: stat([Decimal(x["rounds"][r]["claim_budget_ratio"]) for x in runs
                                       if x["rounds"][r]["claim_budget_ratio"] is not None]) for r in ("1","2")}
    for key in ("total_api_attempts", "api_failed_attempts", "retry_count", "rate_limit_count",
                "parse_failure_count", "parsed_response_count", "unusable_response_count", "unknown_outcome_attempts"):
        result[key] = sum(r[key] for r in runs)
    return result


def format_value(value):
    if value is None:
        return "unknown / unavailable"
    return str(value)


def brief(value):
    return format(Decimal(str(value)), ".6g") if value is not None else "unavailable"


def write_report(batch_folder, config, fixture, runs, planned, stop_reason, simulated):
    measured = [r for r in runs if r["kind"] == "measured"]
    development = [r for r in runs if r["kind"] == "development"]
    overall = batch_stats(measured)
    report = {"simulated": simulated, "model": config["model"], "planned_measured_runs": planned,
              "not_started_measured_runs": planned-len(measured), "stop_reason": stop_reason,
              "development": batch_stats(development), "all_measured_runs": overall,
              "completed_measured_runs_only": batch_stats([r for r in measured if r["run_status"] == "completed"]),
              "runs": [r["run_id"] for r in runs]}
    write_json(batch_folder / "report.json", report)
    lines = ["# Cost pilot report", "", "**SIMULATED OFFLINE DEMO: token counts, claims, and costs are fixtures; elapsed times are local execution only. Not live research evidence.**" if simulated else "Live API pilot; all started runs are retained.", "",
             f"Model: `{config['model']}`; reasoning: none; temperature omitted; output cap: {config['max_output_tokens']}; sequential Responses API.",
             f"Pricing snapshot: {config['pricing']['checked_date']} ([source]({config['pricing']['source']})).",
             f"Measured runs: {len(measured)} started / {planned} planned; {overall['completed']} completed. Stop reason: {stop_reason or 'none'}.",
             f"Development known cost (this batch): ${report['development']['known_cost_usd']}; complete coverage: {report['development']['cost_complete']}.", "",
             "| Run | Kind / outcome | Input / output tokens | Cost USD (or known subtotal) | Wall seconds | Retries / 429 / API failures / parse failures | R1 ratio | R2 ratio |",
             "|---|---|---|---|---|---|---|---|"]
    for r in runs:
        cost = r["estimated_cost_usd"] if r["cost_complete"] else r["known_usage_cost_usd"] + " (partial)"
        lines.append(f"| {r['run_id']} | {r['kind']} / {r['run_status']} ({r['failure_reason'] or 'ok'}) | {format_value(r['input_tokens'])} / {format_value(r['output_tokens'])} | {cost} | {r['wall_clock_seconds']:.3f} | {r['retry_count']} / {r['rate_limit_count']} / {r['api_failed_attempts']} / {r['parse_failure_count']} | {format_value(r['rounds']['1']['claim_budget_ratio'])} | {format_value(r['rounds']['2']['claim_budget_ratio'])} |")
    lines += ["", f"Measured known-cost subtotal: ${overall['known_cost_usd']}; full coverage: {overall['cost_complete']}.",
              f"Effective cost per completed run including failed-run overhead: {format_value(overall['effective_cost_per_completed_run_usd'])} USD.",
              f"Rate limits: {overall['rate_limit_count']} / {overall['total_api_attempts']} dispatched attempts; unknown API outcomes: {overall['unknown_outcome_attempts']}.",
              f"Parse failures: {overall['parse_failure_count']} / {overall['parsed_response_count']} parsed API-successful responses; retries: {overall['retry_count']}.", "",
              "## Observed means and ranges", "", "| Population / metric | N with known value | Mean | Minimum | Maximum |", "|---|---|---|---|---|"]
    for label, group in [("All measured", overall), ("Completed only", report["completed_measured_runs_only"])]:
        for key in ("wall_clock_seconds", "input_tokens", "output_tokens", "total_tokens", "estimated_cost_usd"):
            value = group[key]
            lines.append(f"| {label}: {key} | {value['n'] if value else 0} | {brief(value['mean']) if value else 'unavailable'} | {brief(value['min']) if value else 'unavailable'} | {brief(value['max']) if value else 'unavailable'} |")
    lines += ["", "Unknown values are excluded from the corresponding descriptive mean, not treated as zero. Full-batch cost projections require complete coverage.",
              "Projected costs for 100 / 1,000 attempts of this same configuration: " +
              (f"${overall['projections_usd']['100']} / ${overall['projections_usd']['1000']}." if overall['projections_usd'] else "unavailable."), "",
              "## Claim behavior", "", "| Round | Complete rounds | Mean claims / budget | Minimum | Maximum |",
              "|---|---|---|---|---|"]
    for r, value in overall['round_ratios'].items():
        lines.append(f"| {r} | {value['n'] if value else 0} | {brief(value['mean']) if value else 'unavailable'} | {brief(value['min']) if value else 'unavailable'} | {brief(value['max']) if value else 'unavailable'} |")
    lines += ["", "| Measured run | Claim changes A, B, C, D, E (USD) | Paired claims | Unchanged | Mean absolute change (USD) |", "|---|---|---|---|---|"]
    for r in measured:
        changes = ", ".join(format_value(r['claim_changes_usd'].get(a)) for a in IDS)
        lines.append(f"| {r['run_id']} | {changes} | {r['paired_claim_count']} | {r['unchanged_claim_count']} | {brief(r['mean_absolute_claim_change_usd'])} |")
    if runs:
        example = next((r for r in measured if r["run_status"] == "completed"), runs[0])
        lines += ["", "## Example run", "", f"Run: {example['run_id']}. Ring: A-B-C-D-E-A. Budget: ${config['allocation_budget_usd']:,}.",
                  "", fixture['definition'], "",
                  "| County | Population | Deaths | Rate / 100k | SVI | Poverty % | Rural class |",
                  "|---|---|---|---|---|---|---|"]
        for c in fixture['counties']:
            lines.append(f"| {c['id']} | {c['population']} | {c['overdose_deaths']} | {c['death_rate_per_100k']} | {c['svi']} | {c['poverty_percent']} | {c['rural_class']} |")
        lines += ["", "| County | Round 1 claim USD | Round 2 claim USD | Final allocation USD |", "|---|---|---|---|"]
        for a in IDS:
            claims = [example["rounds"][r]["claims"].get(a, {}).get("claim_amount") for r in ("1", "2")]
            cents = example["allocation_cents"]
            amount = str(Decimal(cents[a])/100) if cents is not None else "unavailable"
            lines.append(f"| {a} | {format_value(claims[0])} | {format_value(claims[1])} | {amount} |")
        lines += ["", "Unallocated budget USD: " + (str(Decimal(example['unallocated_cents']) / 100) if example.get('unallocated_cents') is not None else "unavailable") + "."]
    lines += ["", "Allocator: capped proportional scaling with largest fractional remainders; underclaims are not scaled up. Unpayable fractions of a cent remain unallocated."]
    recommendation = ("Run the live smoke test and measured batch; the offline demo cannot establish model reliability." if simulated else
                      "Review claim transcripts, then consider a limited eight-agent follow-up; this sample is not proof of reliability." if measured and all(r["run_status"] == "completed" for r in measured) else
                      "Resolve the logged access, protocol, or measurement issue before scaling; retain these attempts in the record.")
    lines += ["", "## Recommendation and limits", "", recommendation,
              "Five sequential attempts cannot establish rare-failure rates, causal communication effects, or concurrent rate-limit behavior. Changing model, topology, rounds, message length, or concurrency requires a new measurement.",
              "Literature-positioning and Pennsylvania data-table follow-ups remain separate, as listed in the implementation plan."]
    (batch_folder / "report.md").write_text("\n".join(lines) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true", help="Run fixtures only, without network or credentials")
    mode.add_argument("--live", action="store_true", help="Run one smoke test, then the fixed measured batch")
    parser.add_argument("--config", type=Path, default=BASE/"config.json")
    parser.add_argument("--counties", type=Path, default=BASE/"counties.json")
    parser.add_argument("--env-file", type=Path, help="Optional local dotenv file; never sent to the model")
    args = parser.parse_args(argv)
    config = load_json(args.config.read_text())
    fixture = load_json(args.counties.read_text())
    validate_inputs(config, fixture)
    if args.env_file:
        from dotenv import load_dotenv
        if not args.env_file.is_file():
            parser.error("The specified environment file does not exist")
        load_dotenv(args.env_file, override=False)
    secret = os.environ.get("OPENAI_API_KEY", "") if args.live else ""
    if args.live and not secret:
        parser.error("OPENAI_API_KEY is missing. Set it locally or use --env-file .env. No API requests were sent.")
    root = BASE / "runs" / ("demo" if args.demo else "live")
    root.mkdir(parents=True, exist_ok=True)
    provider = DemoProvider() if args.demo else OpenAIProvider(config, secret)
    with (root / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Another pilot is using this output directory; wait for it to finish")
        guard = SpendGuard(root, config["api_spend_limit_usd"])
        batch = root / ("batch_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:8])
        batch.mkdir()
        runs, stop = [], None
        planned = config["measured_runs"]
        try:
            for index in range(planned + 1):
                kind = "development" if index == 0 else "measured"
                print(f"Starting {kind} run {index or 1}" + (" (SIMULATED)" if args.demo else ""), flush=True)
                summary = run_once(config, fixture, provider, root, kind, guard, args.demo, secret=secret)
                runs.append(summary)
                write_report(batch, config, fixture, runs, planned, stop, args.demo)
                print(f"  {summary['run_status']}: {summary['total_api_attempts']} API attempts, "
                      f"{summary['wall_clock_seconds']:.2f}s; cost coverage {summary['cost_complete']}", flush=True)
                if index == 0 and summary["run_status"] != "completed":
                    stop = "development_smoke_test_failed: " + str(summary["failure_reason"])
                    break
                if summary["fatal_batch_error"] or summary["run_status"] == "interrupted":
                    stop = summary["failure_reason"]
                    break
        except KeyboardInterrupt:
            stop = "keyboard_interrupt_between_runs"
        finally:
            report = write_report(batch, config, fixture, runs, planned, stop, args.demo)
            if hasattr(provider, "close"):
                provider.close()
        print("Report:", batch / "report.md")
        return 0 if len(runs) == planned+1 and all(r["run_status"] == "completed" for r in runs) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, InvalidOperation) as exc:
        print("Pilot setup/artifact error:", type(exc).__name__, "-", str(exc), file=sys.stderr)
        sys.exit(2)
