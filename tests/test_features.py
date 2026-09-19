import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from features import build_feature_frame, POST_HOC_LEAKAGE_COLUMNS  # noqa: E402


def _base_row():
    return {
        "vehicle_model_line": "Touring",
        "dealer_region": "NA-East",
        "component": "engine",
        "vehicle_age_months": 24,
        "mileage_at_claim": 15000,
        "telemetry_fault_codes_30d": 1,
        "telemetry_avg_engine_temp_delta": 2.1,
        "component_historical_failure_severity": 0.3,
        "prior_claims_same_vin": 0,
        "dealer_avg_repair_days": 4.5,
        "escalated": 0,
    }


def test_build_feature_frame_happy_path():
    df = pd.DataFrame([_base_row()])
    out = build_feature_frame(df, is_training=True)
    assert "escalated" in out.columns
    assert "vehicle_model_line_Touring" in out.columns


def test_leakage_columns_rejected():
    row = _base_row()
    row[POST_HOC_LEAKAGE_COLUMNS[0]] = 500.0
    df = pd.DataFrame([row])
    with pytest.raises(ValueError, match="Point-in-time violation"):
        build_feature_frame(df, is_training=True)


def test_missing_column_raises():
    row = _base_row()
    del row["mileage_at_claim"]
    df = pd.DataFrame([row])
    with pytest.raises(ValueError, match="Missing expected columns"):
        build_feature_frame(df, is_training=True)
