"""
Evaluate an existing registered MLflow/XGBoost model.

This is used to establish champion metrics with the same data split,
feature engineering, latency measurement, and segment definitions used
for challenger evaluation.
"""

import argparse
import json
import time
from pathlib import Path

import mlflow.xgboost
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from features import TARGET, build_feature_frame


def evaluate_per_segment(model, X_test, y_test, segment_series, segment_name):
    results = []

    for segment_value in segment_series.unique():
        mask = segment_series == segment_value

        if mask.sum() < 20:
            continue

        preds = model.predict(X_test[mask])

        results.append(
            {
                "segment_type": segment_name,
                "segment_value": segment_value,
                "n": int(mask.sum()),
                "f1": f1_score(y_test[mask], preds, zero_division=0),
            }
        )

    return pd.DataFrame(results)


def main(data_path: str, model_uri: str, output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)

    segment_cols = df[["vehicle_model_line", "dealer_region"]].copy()

    feats = build_feature_frame(df, is_training=True)
    X = feats.drop(columns=[TARGET])
    y = feats[TARGET]

    _, X_test, _, y_test, _, seg_test = train_test_split(
        X,
        y,
        segment_cols,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    print(f"Loading registered champion model from: {model_uri}")
    model = mlflow.xgboost.load_model(model_uri)

    # Align evaluation columns to the exact feature schema expected by
    # the registered XGBoost model.
    expected_features = model.get_booster().feature_names

    if expected_features:
        X_test = X_test.reindex(columns=expected_features, fill_value=0)

    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]

    # Same single-record latency methodology used in train.py.
    latency_ms = []
    latency_sample = X_test.head(min(200, len(X_test)))

    # Warm up the model before collecting latency measurements so one-time
    # initialization/cache effects do not distort the promotion benchmark.
    warmup_sample = latency_sample.head(min(20, len(latency_sample)))
    for i in range(len(warmup_sample)):
        model.predict_proba(warmup_sample.iloc[[i]])

    for i in range(len(latency_sample)):
        row = latency_sample.iloc[[i]]

        start = time.perf_counter()
        model.predict_proba(row)
        latency_ms.append((time.perf_counter() - start) * 1000)

    p95_latency_ms = float(np.percentile(latency_ms, 95))

    metrics = {
        "f1": float(f1_score(y_test, preds)),
        "precision": float(precision_score(y_test, preds)),
        "recall": float(recall_score(y_test, preds)),
        "roc_auc": float(roc_auc_score(y_test, proba)),
        "p95_inference_latency_ms": p95_latency_ms,
    }

    metrics_path = output_path / "metrics.json"

    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("Champion metrics:", metrics)
    print(f"Evaluation metrics written to: {metrics_path}")

    segment_evaluations = [
        ("vehicle_model_line", seg_test["vehicle_model_line"]),
        ("dealer_region", seg_test["dealer_region"]),
    ]

    for name, series in segment_evaluations:
        seg_df = evaluate_per_segment(
            model,
            X_test,
            y_test,
            series,
            name,
        )

        seg_path = output_path / f"segment_eval_{name}.csv"
        seg_df.to_csv(seg_path, index=False)

        print(f"\nPer-segment F1 ({name}):\n{seg_df}")
        print(f"Segment evaluation written to: {seg_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_path", type=str, required=True)
    parser.add_argument("--model_uri", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)

    args = parser.parse_args()

    main(
        args.data_path,
        args.model_uri,
        args.output_dir,
    )
