"""
Drift monitoring — distinguishes data drift, concept drift, and prediction
drift explicitly, because they call for different responses. See
docs/DECISIONS.md and interview notes for the reasoning; this script is the
mechanical implementation of that framework.

- Data drift: input distribution shifted (e.g. claim volumes for one model
  line skewing toward a different repair severity than the model trained
  on). A warning to investigate, not proof the model is wrong.
- Prediction drift: the model's OWN output distribution shifted (e.g. flagged
  rate jumps from 5% to 30% of claims). Could be a real business change or a
  problem — check data drift and concept drift before assuming either.
- Concept drift: the relationship between inputs and the true label changed.
  Only detectable once real labeled outcomes come back in, so it's checked
  separately on a delayed cadence, not in this real-time script.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

PSI_ALERT_THRESHOLD = 0.2   # population stability index — >0.2 is a commonly used "significant shift" line
PREDICTION_RATE_ALERT_DELTA = 0.10  # 10 percentage point swing in flagged rate


def population_stability_index(expected: pd.Series, actual: pd.Series, buckets: int = 10) -> float:
    breakpoints = np.quantile(expected, np.linspace(0, 1, buckets + 1))
    breakpoints[0], breakpoints[-1] = -np.inf, np.inf

    expected_pct = pd.cut(expected, breakpoints).value_counts(normalize=True, sort=False)
    actual_pct = pd.cut(actual, breakpoints).value_counts(normalize=True, sort=False)

    expected_pct = expected_pct.replace(0, 1e-6)
    actual_pct = actual_pct.replace(0, 1e-6)

    return float(((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)).sum())


def check_data_drift(training_features: pd.DataFrame, live_features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in training_features.select_dtypes(include=[np.number]).columns:
        psi = population_stability_index(training_features[col], live_features[col])
        ks_stat, ks_p = ks_2samp(training_features[col], live_features[col])
        rows.append({
            "feature": col,
            "psi": psi,
            "ks_statistic": ks_stat,
            "ks_p_value": ks_p,
            "alert": psi > PSI_ALERT_THRESHOLD,
        })
    return pd.DataFrame(rows)


def check_prediction_drift(training_predictions_rate: float, live_predictions_rate: float) -> dict:
    delta = live_predictions_rate - training_predictions_rate
    return {
        "training_flagged_rate": training_predictions_rate,
        "live_flagged_rate": live_predictions_rate,
        "delta": delta,
        "alert": abs(delta) > PREDICTION_RATE_ALERT_DELTA,
        "note": (
            "A shift this size needs data-drift and concept-drift checked "
            "before assuming either a real business change or a model "
            "problem — do not act on this signal alone."
        ),
    }
