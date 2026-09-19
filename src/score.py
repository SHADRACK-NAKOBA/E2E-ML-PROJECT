"""
Entry script for the Azure ML managed online endpoint.

Uses the SAME feature logic as training (features.py) — this is the whole
point of sharing that module, so serving can never silently diverge from
what the model was trained on.
"""
import json
import os

import mlflow
import pandas as pd
import shap

from features import build_feature_frame

model = None
explainer = None


def init():
    global model, explainer
    model_dir = os.getenv("AZUREML_MODEL_DIR")
    model_path = os.path.join(model_dir, "model")
    model = mlflow.xgboost.load_model(model_path)  # matches mlflow.xgboost.log_model in train.py
    explainer = shap.TreeExplainer(model)


def run(raw_data: str) -> str:
    payload = json.loads(raw_data)
    df = pd.DataFrame(payload["instances"])

    feats = build_feature_frame(df, is_training=False)
    # ensure column order/one-hot columns match training exactly; any column
    # the trained booster expects but the request lacks is filled with 0
    feats = feats.reindex(columns=model.get_booster().feature_names, fill_value=0)

    proba = model.predict_proba(feats)[:, 1]
    shap_values = explainer.shap_values(feats)

    results = []
    for i, claim_id in enumerate(payload.get("claim_ids", range(len(df)))):
        # SHAP tells you what the model weighted, not what caused the
        # outcome — the API response is worded that way deliberately.
        top_factors = (
            pd.Series(shap_values[i], index=feats.columns)
            .abs()
            .sort_values(ascending=False)
            .head(5)
            .index.tolist()
        )
        results.append({
            "claim_id": claim_id,
            "escalation_risk_score": float(proba[i]),
            "high_risk": bool(proba[i] > 0.5),
            "top_weighted_factors": top_factors,
        })

    return json.dumps({"predictions": results})
