import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from promote_challenger import evaluate_promotion


@pytest.fixture
def segment_csvs(tmp_path):
    champ = pd.DataFrame({"segment_value": ["Touring", "Sportster"], "f1": [0.80, 0.78]})
    chall_ok = pd.DataFrame({"segment_value": ["Touring", "Sportster"], "f1": [0.83, 0.79]})
    chall_regression = pd.DataFrame({"segment_value": ["Touring", "Sportster"], "f1": [0.83, 0.60]})

    champ_path = tmp_path / "champ.csv"
    ok_path = tmp_path / "chall_ok.csv"
    reg_path = tmp_path / "chall_reg.csv"
    champ.to_csv(champ_path, index=False)
    chall_ok.to_csv(ok_path, index=False)
    chall_regression.to_csv(reg_path, index=False)
    return str(champ_path), str(ok_path), str(reg_path)


def test_promotion_approved_when_all_gates_pass(segment_csvs):
    champ_path, ok_path, _ = segment_csvs
    approved, reasons = evaluate_promotion(
        champion_f1=0.80, challenger_f1=0.83,
        champion_p95_latency_ms=200, challenger_p95_latency_ms=210,
        champion_segment_csv=champ_path, challenger_segment_csv=ok_path,
    )
    assert approved
    assert reasons == []


def test_promotion_blocked_on_segment_fairness_regression(segment_csvs):
    champ_path, _, reg_path = segment_csvs
    approved, reasons = evaluate_promotion(
        champion_f1=0.80, challenger_f1=0.83,
        champion_p95_latency_ms=200, challenger_p95_latency_ms=210,
        champion_segment_csv=champ_path, challenger_segment_csv=reg_path,
    )
    assert not approved
    assert any("fairness regression" in r for r in reasons)


def test_promotion_blocked_on_lower_aggregate_f1(segment_csvs):
    champ_path, ok_path, _ = segment_csvs
    approved, reasons = evaluate_promotion(
        champion_f1=0.80, challenger_f1=0.79,
        champion_p95_latency_ms=200, challenger_p95_latency_ms=205,
        champion_segment_csv=champ_path, challenger_segment_csv=ok_path,
    )
    assert not approved
    assert any("does not beat champion" in r for r in reasons)
