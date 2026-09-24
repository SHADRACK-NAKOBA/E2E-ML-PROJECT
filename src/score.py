"""
Entry script for the Azure ML managed online endpoint.

Uses the SAME feature logic as training (features.py) and then aligns the
serving feature frame to the exact schema used to train the registered model.
"""
import json
import os

import mlflow
import pandas as pd
import shap

from features import build_feature_frame


EXPECTED_FEATURES = [
    "vehicle_age_months",
    "mileage_at_claim",
    "telemetry_fault_codes_30d",
    "telemetry_avg_engine_temp_delta",
    "component_historical_failure_severity",
    "prior_claims_same_vin",
    "dealer_avg_repair_days",
    "vehicle_model_line_Adventure",
    "vehicle_model_line_CVO",
    "vehicle_model_line_Softail",
    "vehicle_model_line_Sportster",
    "vehicle_model_line_Touring",
    "dealer_region_APAC",
    "dealer_region_EMEA",
    "dealer_region_LATAM",
    "dealer_region_NA-East",
    "dealer_region_NA-West",
    "component_brakes",
    "component_electrical",
    "component_engine",
    "component_suspension",
    "component_telematics_unit",
    "component_transmission",
]

model = None
explainer = None


def init():
    global model, explainer
    model_dir = os.getenv("AZUREML_MODEL_DIR")
    model_path = os.path.join(model_dir, "model")
    model = mlflow.xgboost.load_model(model_path)
    explainer = shap.TreeExplainer(model)


def run(raw_data: str) -> str:
    payload = json.loads(raw_data)
    df = pd.DataFrame(payload["instances"])

    feats = build_feature_frame(df, is_training=False)

    # A single request only creates dummy columns for categories present
    # in that request. Reindex to the complete training schema.
    feats = feats.reindex(columns=EXPECTED_FEATURES, fill_value=0)

    proba = model.predict_proba(feats)[:, 1]
    shap_values = explainer.shap_values(feats)

    results = []
    for i, claim_id in enumerate(payload.get("claim_ids", range(len(df)))):
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
