"""
run_experiment.py

Runs the same 100 repair requests through the naive agent twice - once
against api_v1 (human-shaped), once against api_v2 (agent-shaped) - and
scores the outcomes.

Usage:
    python3 run_experiment.py
"""

import csv
import json
from pathlib import Path

from requests_sample import generate_requests
from api_v1 import V1Client
from api_v2 import V2Client
from agent import run_agent_v1, run_agent_v2
from catalogue import CATALOGUE

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def part_is_superseded(part_number: str) -> bool:
    for p in CATALOGUE:
        if p.part_number == part_number:
            return p.superseded_by is not None
    return False


def score_outcomes(outcomes, requests_by_id):
    rows = []
    for out in outcomes:
        req = requests_by_id[out.request_id]

        # Post-hoc ground-truth check (not visible to the agent while it
        # ran): did it silently order a part that's since been superseded?
        silently_obsolete = False
        if out.ordered_part_number and part_is_superseded(out.ordered_part_number):
            silently_obsolete = True
            if not out.escalated_to_human:
                out.wrong_part = True
                if out.notes:
                    out.notes += "; "
                out.notes += "ordered a superseded/obsolete part without flagging it"

        rows.append({
            "request_id": out.request_id,
            "api_version": out.api_version,
            "vehicle_id": req.vehicle_id,
            "part_type": req.part_type,
            "side_stated": req.stated_side,
            "side_actual": req.actual_side,
            "simulated_timeout": req.simulate_timeout,
            "tool_calls": out.tool_calls,
            "ordered_part_number": out.ordered_part_number,
            "wrong_part": out.wrong_part,
            "silently_obsolete": silently_obsolete,
            "duplicate_order": out.duplicate_order,
            "escalated_to_human": out.escalated_to_human,
            "notes": out.notes,
        })
    return rows


def summarise(rows, label):
    n = len(rows)
    wrong = sum(1 for r in rows if r["wrong_part"])
    obsolete = sum(1 for r in rows if r["silently_obsolete"])
    dup = sum(1 for r in rows if r["duplicate_order"])
    escalated = sum(1 for r in rows if r["escalated_to_human"])
    total_calls = sum(r["tool_calls"] for r in rows)

    return {
        "api_version": label,
        "n_requests": n,
        "wrong_part_count": wrong,
        "wrong_part_rate": round(wrong / n, 3),
        "silently_obsolete_count": obsolete,
        "duplicate_order_count": dup,
        "duplicate_order_rate": round(dup / n, 3),
        "escalated_to_human_count": escalated,
        "escalated_to_human_rate": round(escalated / n, 3),
        "avg_tool_calls": round(total_calls / n, 2),
    }


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    requests = generate_requests(100)
    requests_by_id = {r.request_id: r for r in requests}

    v1_client = V1Client()
    v2_client = V2Client()

    v1_outcomes = [run_agent_v1(r, v1_client) for r in requests]
    v2_outcomes = [run_agent_v2(r, v2_client) for r in requests]

    v1_rows = score_outcomes(v1_outcomes, requests_by_id)
    v2_rows = score_outcomes(v2_outcomes, requests_by_id)

    all_rows = v1_rows + v2_rows
    fieldnames = list(all_rows[0].keys())
    with open(RESULTS_DIR / "raw_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    v1_summary = summarise(v1_rows, "v1_human_shaped")
    v2_summary = summarise(v2_rows, "v2_agent_shaped")

    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump({"v1_human_shaped": v1_summary, "v2_agent_shaped": v2_summary}, f, indent=2)

    print_report(v1_summary, v2_summary)


def print_report(v1_summary, v2_summary):
    print("=" * 72)
    print(f"{'metric':<28}{'v1 (human-shaped)':<24}{'v2 (agent-shaped)':<20}")
    print("-" * 72)

    def row(label, key, as_pct=False):
        a = v1_summary[key]
        b = v2_summary[key]
        if as_pct:
            a, b = f"{a*100:.1f}%", f"{b*100:.1f}%"
        print(f"{label:<28}{str(a):<24}{str(b):<20}")

    row("Requests", "n_requests")
    row("Wrong part ordered", "wrong_part_count")
    row("Wrong part rate", "wrong_part_rate", as_pct=True)
    row("Silently ordered obsolete", "silently_obsolete_count")
    row("Duplicate orders", "duplicate_order_count")
    row("Duplicate order rate", "duplicate_order_rate", as_pct=True)
    row("Escalated to human", "escalated_to_human_count")
    row("Escalation rate", "escalated_to_human_rate", as_pct=True)
    row("Avg tool calls / request", "avg_tool_calls")
    print("=" * 72)
    print("\nFull row-level detail: results/raw_results.csv")
    print("Summary JSON: results/summary.json")


if __name__ == "__main__":
    main()
