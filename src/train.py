"""
Training entry point for the escalation-risk model.

Run as an Azure ML job (see jobs/train-job.yml), never interactively — every
run this way leaves a durable MLflow record of the exact code version, data
reference, and environment that produced the model. That lineage is what
lets a finance or service-quality reviewer ask "why did the model flag this
claim" months later and get a real answer instead of a guess.
"""
import argparse

import mlflow
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from features import TARGET, build_feature_frame


def evaluate_per_segment(model, X_test, y_test, segment_series, segment_name):
    """Per-segment evaluation — a model that's better in aggregate but worse
    for one vehicle model line or dealer region is a fairness problem, not
    just a performance number. See docs/DECISIONS.md #9."""
    results = []
    for segment_value in segment_series.unique():
        mask = segment_series == segment_value
        if mask.sum() < 20:  # too few samples for a meaningful per-segment score
            continue
        preds = model.predict(X_test[mask])
        results.append({
            "segment_type": segment_name,
            "segment_value": segment_value,
            "n": int(mask.sum()),
            "f1": f1_score(y_test[mask], preds, zero_division=0),
        })
    return pd.DataFrame(results)


def main(data_path: str, n_estimators: int, max_depth: int, learning_rate: float):
    mlflow.autolog()

    df = pd.read_csv(data_path)
    # keep raw segment columns for per-segment eval before one-hot encoding
    segment_cols = df[["vehicle_model_line", "dealer_region"]].copy()

    feats = build_feature_frame(df, is_training=True)
    X = feats.drop(columns=[TARGET])
    y = feats[TARGET]

    X_train, X_test, y_train, y_test, _seg_train, seg_test = train_test_split(
        X, y, segment_cols, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "f1": f1_score(y_test, preds),
        "precision": precision_score(y_test, preds),
        "recall": recall_score(y_test, preds),
        "roc_auc": roc_auc_score(y_test, proba),
    }
    mlflow.log_metrics(metrics)
    print("Overall metrics:", metrics)

    for name, series in [("vehicle_model_line", seg_test["vehicle_model_line"]),
                          ("dealer_region", seg_test["dealer_region"])]:
        seg_df = evaluate_per_segment(model, X_test, y_test, series, name)
        seg_path = f"segment_eval_{name}.csv"
        seg_df.to_csv(seg_path, index=False)
        mlflow.log_artifact(seg_path)
        print(f"\nPer-segment F1 ({name}):\n{seg_df}")

    # mlflow.sklearn wraps models via skops, which does not trust XGBoost's
    # native Booster type by default (as of mlflow>=2.11 / skops security
    # hardening). XGBClassifier needs the xgboost-specific flavor, not the
    # generic sklearn one, even though it exposes the sklearn API.
    mlflow.xgboost.log_model(model, artifact_path="model")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, required=True)
    parser.add_argument("--n_estimators", type=int, default=300)
    parser.add_argument("--max_depth", type=int, default=5)
    parser.add_argument("--learning_rate", type=float, default=0.05)
    args = parser.parse_args()

    main(args.data_path, args.n_estimators, args.max_depth, args.learning_rate)
