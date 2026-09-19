"""
Generates synthetic connected-vehicle warranty/service claims data.

Nakoba is a portfolio project — it never touches real customer, dealer, or
vehicle data. This generator produces a plausible claims dataset with the
same shape and known label-generating logic, so the rest of the pipeline
(features, training, evaluation, drift monitoring) is fully runnable and the
label mechanism is inspectable rather than a black box.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(seed=42)

VEHICLE_MODEL_LINES = ["Touring", "Sportster", "Softail", "CVO", "Adventure"]
DEALER_REGIONS = ["NA-East", "NA-West", "EMEA", "APAC", "LATAM"]
COMPONENTS = ["engine", "transmission", "electrical", "brakes", "suspension", "telematics_unit"]


def generate(n_rows: int = 20_000) -> pd.DataFrame:
    df = pd.DataFrame({
        "claim_id": [f"CLM-{i:07d}" for i in range(n_rows)],
        "vehicle_model_line": RNG.choice(VEHICLE_MODEL_LINES, n_rows),
        "dealer_region": RNG.choice(DEALER_REGIONS, n_rows),
        "component": RNG.choice(COMPONENTS, n_rows),
        "vehicle_age_months": RNG.integers(1, 96, n_rows),
        "mileage_at_claim": RNG.integers(100, 60_000, n_rows),
        # H-D-Connect-style telemetry signal, synthetic
        "telemetry_fault_codes_30d": RNG.poisson(0.6, n_rows),
        "telemetry_avg_engine_temp_delta": RNG.normal(0, 5, n_rows),
        "component_historical_failure_severity": RNG.beta(2, 5, n_rows),  # point-in-time feature, see features.py
        "prior_claims_same_vin": RNG.poisson(0.3, n_rows),
        "dealer_avg_repair_days": RNG.gamma(3, 2, n_rows),
    })

    # Ground-truth label logic (known, so drift/eval behavior is inspectable):
    # escalation risk rises with fault codes, historical severity, prior claims,
    # and is modestly noisier for older vehicles.
    risk_score = (
        0.35 * df["telemetry_fault_codes_30d"]
        + 2.2 * df["component_historical_failure_severity"]
        + 0.5 * df["prior_claims_same_vin"]
        + 0.01 * df["vehicle_age_months"]
        + RNG.normal(0, 0.6, n_rows)
    )
    threshold = np.quantile(risk_score, 0.85)  # ~15% base escalation rate
    df["escalated"] = (risk_score > threshold).astype(int)

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=20_000)
    parser.add_argument("--out", type=str, default="data/synthetic_claims.csv")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    generate(args.rows).to_csv(out_path, index=False)
    print(f"Wrote {args.rows} synthetic claims to {out_path}")
