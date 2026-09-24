import pandas as pd
import pytest

from scripts.promote_challenger import evaluate_promotion


@pytest.fixture
def segment_csvs(tmp_path):
    # Champion baseline for both fairness dimensions.
    champion = pd.DataFrame(
        {
            "segment_value": ["A", "B", "C"],
            "f1": [0.80, 0.82, 0.78],
        }
    )

    # Challenger stays within the allowed 0.03 segment-F1 regression.
    challenger_ok = pd.DataFrame(
        {
            "segment_value": ["A", "B", "C"],
            "f1": [0.81, 0.82, 0.79],
        }
    )

    # Challenger has a material regression for segment B.
    challenger_regression = pd.DataFrame(
        {
            "segment_value": ["A", "B", "C"],
            "f1": [0.81, 0.70, 0.79],
        }
    )

    champion_path = tmp_path / "champion.csv"
    challenger_ok_path = tmp_path / "challenger_ok.csv"
    challenger_regression_path = tmp_path / "challenger_regression.csv"

    champion.to_csv(champion_path, index=False)
    challenger_ok.to_csv(challenger_ok_path, index=False)
    challenger_regression.to_csv(challenger_regression_path, index=False)

    return (
        str(champion_path),
        str(challenger_ok_path),
        str(challenger_regression_path),
    )


def test_promotion_approved_when_all_gates_pass(segment_csvs):
    champion_path, challenger_ok_path, _ = segment_csvs

    approved, reasons = evaluate_promotion(
        champion_f1=0.80,
        challenger_f1=0.83,
        champion_p95_latency_ms=200,
        challenger_p95_latency_ms=210,
        champion_dealer_region_csv=champion_path,
        challenger_dealer_region_csv=challenger_ok_path,
        champion_vehicle_model_line_csv=champion_path,
        challenger_vehicle_model_line_csv=challenger_ok_path,
    )

    assert approved is True
    assert reasons == []


def test_promotion_blocked_on_segment_fairness_regression(segment_csvs):
    champion_path, _, challenger_regression_path = segment_csvs

    approved, reasons = evaluate_promotion(
        champion_f1=0.80,
        challenger_f1=0.83,
        champion_p95_latency_ms=200,
        challenger_p95_latency_ms=210,
        champion_dealer_region_csv=champion_path,
        challenger_dealer_region_csv=challenger_regression_path,
        champion_vehicle_model_line_csv=champion_path,
        challenger_vehicle_model_line_csv=champion_path,
    )

    assert approved is False
    assert any("dealer_region" in reason for reason in reasons)


def test_promotion_blocked_on_lower_aggregate_f1(segment_csvs):
    champion_path, challenger_ok_path, _ = segment_csvs

    approved, reasons = evaluate_promotion(
        champion_f1=0.80,
        challenger_f1=0.79,
        champion_p95_latency_ms=200,
        challenger_p95_latency_ms=205,
        champion_dealer_region_csv=champion_path,
        challenger_dealer_region_csv=challenger_ok_path,
        champion_vehicle_model_line_csv=champion_path,
        challenger_vehicle_model_line_csv=challenger_ok_path,
    )

    assert approved is False
    assert any("does not beat champion" in reason for reason in reasons)