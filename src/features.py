"""
Shared feature definitions for training AND serving.

This module exists specifically to prevent training-serving skew: a feature
like "component's historical failure severity for this model line" must be
computed identically in both paths, and must respect point-in-time
correctness — training data can never use information that wouldn't have
actually been available at the moment a real service technician saw the
claim. Warranty data is especially prone to this because many fields get
updated retroactively as a repair progresses (e.g. final repair cost, final
severity classification) — those are exactly the columns that must be
excluded from a "claim intake" feature set.
"""
from __future__ import annotations

import pandas as pd

# Columns known only AFTER a repair completes — never eligible as model
# inputs, since they would not exist at claim-intake / scoring time.
POST_HOC_LEAKAGE_COLUMNS = [
    "final_repair_cost",
    "final_severity_classification",
    "repair_completed_at",
    "technician_notes_final",
]

CATEGORICAL_FEATURES = ["vehicle_model_line", "dealer_region", "component"]

NUMERIC_FEATURES = [
    "vehicle_age_months",
    "mileage_at_claim",
    "telemetry_fault_codes_30d",
    "telemetry_avg_engine_temp_delta",
    "component_historical_failure_severity",
    "prior_claims_same_vin",
    "dealer_avg_repair_days",
]

TARGET = "escalated"


def build_feature_frame(df: pd.DataFrame, *, is_training: bool = True) -> pd.DataFrame:
    """Single entry point used by both the training script and the scoring
    script, so there is exactly one place feature logic can drift."""
    leaked = [c for c in POST_HOC_LEAKAGE_COLUMNS if c in df.columns]
    if leaked:
        raise ValueError(
            f"Point-in-time violation: post-repair columns present in an "
            f"intake-time feature frame: {leaked}. These are only known "
            f"after a claim resolves and must never reach the model."
        )

    cols = CATEGORICAL_FEATURES + NUMERIC_FEATURES
    if is_training:
        cols = cols + [TARGET]

    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")

    out = df[cols].copy()
    out = pd.get_dummies(out, columns=CATEGORICAL_FEATURES, drop_first=False)
    return out
