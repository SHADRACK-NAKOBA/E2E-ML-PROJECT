"""
Challenger-vs-champion promotion gate.

A higher aggregate F1 alone is NOT a promotion decision. A model that's
slightly more accurate overall but systematically worse for one vehicle
model line or dealer region is an operational-fairness problem — see
docs/DECISIONS.md #9.

This script evaluates aggregate model quality, inference latency, and
segment-level F1 across both dealer region and vehicle model line.
It fails loudly (nonzero exit) before any canary traffic shift.
"""

import argparse
import sys

import pandas as pd


MAX_ALLOWED_LATENCY_REGRESSION_MS = 50
MAX_ALLOWED_SEGMENT_F1_DROP = 0.03


def evaluate_segment_dimension(
    dimension_name: str,
    champion_csv: str,
    challenger_csv: str,
) -> list[str]:
    """Compare champion and challenger F1 for one segment dimension."""
    reasons = []

    champion = pd.read_csv(champion_csv).set_index("segment_value")["f1"]
    challenger = pd.read_csv(challenger_csv).set_index("segment_value")["f1"]

    for segment, champion_f1 in champion.items():
        if segment not in challenger.index:
            reasons.append(
                f"{dimension_name} segment '{segment}' is missing from "
                "challenger evaluation."
            )
            continue

        challenger_f1 = challenger.loc[segment]
        drop = champion_f1 - challenger_f1

        if drop > MAX_ALLOWED_SEGMENT_F1_DROP:
            reasons.append(
                f"{dimension_name} segment '{segment}' F1 drops by "
                f"{drop:.3f} under the challenger "
                f"(limit {MAX_ALLOWED_SEGMENT_F1_DROP:.3f})."
            )

    return reasons


def evaluate_promotion(
    champion_f1: float,
    challenger_f1: float,
    champion_p95_latency_ms: float,
    challenger_p95_latency_ms: float,
    champion_dealer_region_csv: str,
    challenger_dealer_region_csv: str,
    champion_vehicle_model_line_csv: str,
    challenger_vehicle_model_line_csv: str,
) -> tuple[bool, list[str]]:
    reasons = []

    if challenger_f1 <= champion_f1:
        reasons.append(
            f"Challenger F1 ({challenger_f1:.4f}) does not beat "
            f"champion ({champion_f1:.4f})."
        )

    latency_delta = challenger_p95_latency_ms - champion_p95_latency_ms

    if latency_delta > MAX_ALLOWED_LATENCY_REGRESSION_MS:
        reasons.append(
            f"Challenger p95 latency regresses by {latency_delta:.2f}ms "
            f"(limit {MAX_ALLOWED_LATENCY_REGRESSION_MS}ms)."
        )

    reasons.extend(
        evaluate_segment_dimension(
            "dealer_region",
            champion_dealer_region_csv,
            challenger_dealer_region_csv,
        )
    )

    reasons.extend(
        evaluate_segment_dimension(
            "vehicle_model_line",
            champion_vehicle_model_line_csv,
            challenger_vehicle_model_line_csv,
        )
    )

    return len(reasons) == 0, reasons


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--champion-f1", type=float, required=True)
    parser.add_argument("--challenger-f1", type=float, required=True)

    parser.add_argument("--champion-p95-ms", type=float, required=True)
    parser.add_argument("--challenger-p95-ms", type=float, required=True)

    parser.add_argument(
        "--champion-dealer-region-csv",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--challenger-dealer-region-csv",
        type=str,
        required=True,
    )

    parser.add_argument(
        "--champion-vehicle-model-line-csv",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--challenger-vehicle-model-line-csv",
        type=str,
        required=True,
    )

    args = parser.parse_args()

    approved, reasons = evaluate_promotion(
        args.champion_f1,
        args.challenger_f1,
        args.champion_p95_ms,
        args.challenger_p95_ms,
        args.champion_dealer_region_csv,
        args.challenger_dealer_region_csv,
        args.champion_vehicle_model_line_csv,
        args.challenger_vehicle_model_line_csv,
    )

    if approved:
        print("PROMOTION APPROVED. Challenger clears all gates.")
        sys.exit(0)

    print("PROMOTION BLOCKED:")
    for reason in reasons:
        print(f"  - {reason}")

    sys.exit(2)