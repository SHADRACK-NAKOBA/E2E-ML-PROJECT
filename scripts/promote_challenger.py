"""
Challenger-vs-champion promotion gate.

A higher aggregate F1 alone is NOT a promotion decision. A model that's
slightly more accurate overall but systematically worse for one vehicle
model line or dealer region is an operational-fairness problem — see
docs/DECISIONS.md #9. This script fails loudly (nonzero exit) rather than
promoting silently, and is meant to be the CD pipeline's gate before any
canary traffic shift.
"""
import argparse
import sys

import pandas as pd

MAX_ALLOWED_LATENCY_REGRESSION_MS = 50
MAX_ALLOWED_SEGMENT_F1_DROP = 0.03  # a challenger can't be >3pt worse F1 for any segment, even if it wins overall


def evaluate_promotion(
    champion_f1: float,
    challenger_f1: float,
    champion_p95_latency_ms: float,
    challenger_p95_latency_ms: float,
    champion_segment_csv: str,
    challenger_segment_csv: str,
) -> tuple[bool, list[str]]:
    reasons = []

    if challenger_f1 <= champion_f1:
        reasons.append(f"Challenger F1 ({challenger_f1:.4f}) does not beat champion ({champion_f1:.4f}).")

    latency_delta = challenger_p95_latency_ms - champion_p95_latency_ms
    if latency_delta > MAX_ALLOWED_LATENCY_REGRESSION_MS:
        reasons.append(
            f"Challenger p95 latency regresses by {latency_delta:.0f}ms "
            f"(limit {MAX_ALLOWED_LATENCY_REGRESSION_MS}ms)."
        )

    champ_seg = pd.read_csv(champion_segment_csv).set_index("segment_value")["f1"]
    chall_seg = pd.read_csv(challenger_segment_csv).set_index("segment_value")["f1"]
    for segment, champ_f1 in champ_seg.items():
        if segment not in chall_seg.index:
            continue
        drop = champ_f1 - chall_seg[segment]
        if drop > MAX_ALLOWED_SEGMENT_F1_DROP:
            reasons.append(
                f"Segment '{segment}' F1 drops by {drop:.3f} under the challenger "
                f"(limit {MAX_ALLOWED_SEGMENT_F1_DROP}) — a fairness regression, "
                f"not just a performance one."
            )

    return (len(reasons) == 0), reasons


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--champion-f1", type=float, required=True)
    parser.add_argument("--challenger-f1", type=float, required=True)
    parser.add_argument("--champion-p95-ms", type=float, required=True)
    parser.add_argument("--challenger-p95-ms", type=float, required=True)
    parser.add_argument("--champion-segment-csv", type=str, required=True)
    parser.add_argument("--challenger-segment-csv", type=str, required=True)
    args = parser.parse_args()

    approved, reasons = evaluate_promotion(
        args.champion_f1, args.challenger_f1,
        args.champion_p95_ms, args.challenger_p95_ms,
        args.champion_segment_csv, args.challenger_segment_csv,
    )

    if approved:
        print("PROMOTION APPROVED. Challenger clears all gates.")
        sys.exit(0)
    else:
        print("PROMOTION BLOCKED:")
        for r in reasons:
            print(f"  - {r}")
        sys.exit(1)
