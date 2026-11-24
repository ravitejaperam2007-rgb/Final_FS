"""
AWARE-AI — SHAP Model Explainability Engine

Provides:
- Global feature importance analysis using TreeSHAP.
- Individual shipment waterfall explanations decomposing why a specific shipment is flagged as delayed.
- Serialized attribution outputs ready for Streamlit visualizations and database persistence.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import shap

from ml.models.risk_predictor import ShipmentDelayPredictor
from ml.pipelines.pipeline import FEATURE_NAMES, ShipmentFeaturePipeline
from utils.logger import get_logger

logger = get_logger("ml.explainability.shap")


class ShapExplainer:
    """
    SHAP explanation engine for LightGBM tree boosters.
    Computes exact Shapley values for individual shipment delay predictions.
    """

    def __init__(self, predictor: Optional[ShipmentDelayPredictor] = None):
        self.predictor = predictor or ShipmentDelayPredictor()
        if self.predictor.booster is None:
            self.predictor.train_baseline_model()

        # Initialize TreeExplainer on the LightGBM booster
        self.tree_explainer = shap.TreeExplainer(self.predictor.booster)

    def explain_instance(self, features_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate local explanation for a single shipment instance.
        Returns base value, SHAP contribution per feature, and top risk drivers.
        """
        X = features_df[FEATURE_NAMES]
        shap_values = self.tree_explainer.shap_values(X)

        # For binary classification TreeExplainer, shap_values can be a list or array
        if isinstance(shap_values, list):
            sv = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
        else:
            sv = shap_values[0] if len(shap_values.shape) > 1 else shap_values

        base_val = float(self.tree_explainer.expected_value[1] if isinstance(self.tree_explainer.expected_value, (list, np.ndarray)) else self.tree_explainer.expected_value)

        attributions: Dict[str, float] = {}
        for feat_name, val in zip(FEATURE_NAMES, sv):
            attributions[feat_name] = round(float(val), 4)

        # Sort feature impact by absolute SHAP magnitude
        sorted_drivers = sorted(
            attributions.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )

        return {
            "base_value": round(base_val, 4),
            "attributions": attributions,
            "top_positive_drivers": [
                {"feature": k, "impact": v, "value": float(X[k].iloc[0])}
                for k, v in sorted_drivers if v > 0
            ][:3],
            "top_mitigating_factors": [
                {"feature": k, "impact": v, "value": float(X[k].iloc[0])}
                for k, v in sorted_drivers if v < 0
            ][:3],
        }

    def explain_raw_features(self, raw_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convenience wrapper to extract features and compute local SHAP explanation.
        """
        df = ShipmentFeaturePipeline.transform_single(raw_features)
        explanation = self.explain_instance(df)
        explanation["input_values"] = {col: float(df[col].iloc[0]) for col in FEATURE_NAMES}
        return explanation

    def get_global_feature_importance(self) -> List[Dict[str, Any]]:
        """
        Extract global feature importance from LightGBM gain.
        """
        importance_gain = self.predictor.booster.feature_importance(importance_type="gain")
        total_gain = float(np.sum(importance_gain)) or 1.0

        records = []
        for name, gain in zip(FEATURE_NAMES, importance_gain):
            records.append({
                "feature": name,
                "importance_gain": round(float(gain), 2),
                "importance_pct": round((float(gain) / total_gain) * 100.0, 2),
            })

        records.sort(key=lambda x: x["importance_pct"], reverse=True)
        return records
