"""
AWARE-AI — Machine Learning End-to-End Prediction & Explainability Pipeline

Orchestrates:
1. Operational feature extraction from database entities.
2. LightGBM delay probability prediction.
3. Multi-factor composite risk scoring & risk classification.
4. SHAP local attribution generation.
5. Persistent logging into the MLPrediction and RiskAssessment database tables.
6. Retrieval of prediction and explanation history.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.connection import DatabaseManager
from database.crud import (
    InventoryCRUD,
    MLPredictionCRUD,
    PortCRUD,
    RiskCRUD,
    ShipmentCRUD,
    SupplierCRUD,
)
from database.models import MLPrediction, RiskAssessment, RiskLevel
from ml.explainability.shap_explainer import ShapExplainer
from ml.models.risk_predictor import ShipmentDelayPredictor
from ml.pipelines.pipeline import ShipmentFeaturePipeline
from modules.shipment.routes import RouteOptimizer
from utils.logger import get_logger

logger = get_logger("ml.pipelines.engine")


class MLExplainabilityPipeline:
    """
    End-to-End ML Prediction and SHAP explanation pipeline integrated with SQLite.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        predictor: Optional[ShipmentDelayPredictor] = None,
        explainer: Optional[ShapExplainer] = None,
    ):
        self.db = db_manager
        self.predictor = predictor or ShipmentDelayPredictor()
        self.explainer = explainer or ShapExplainer(self.predictor)

    def predict_and_explain_shipment(
        self,
        shipment_id: int,
        weather_override: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluate live ML delay probability, composite risk, and SHAP attribution for a shipment.
        Persists full audit trail to the database.
        """
        with self.db.session() as session:
            shipment = ShipmentCRUD.get(session, shipment_id)
            if not shipment:
                raise ValueError(f"Shipment {shipment_id} does not exist.")

            origin = PortCRUD.get(session, shipment.origin_port_id)
            dest = PortCRUD.get(session, shipment.destination_port_id)
            supplier = SupplierCRUD.get(session, shipment.supplier_id) if shipment.supplier_id else None

            # Calculate route distance
            distance_nm = 1200.0
            if origin and dest:
                distance_nm = RouteOptimizer.haversine_distance_nm(
                    origin.latitude, origin.longitude,
                    dest.latitude, dest.longitude,
                )

            # Downstream inventory risk
            inv_stockout_risk = 0.20
            if supplier:
                low_stock_items = InventoryCRUD.list_low_stock(session)
                sup_items = [i for i in low_stock_items if i.supplier_id == supplier.id]
                if sup_items:
                    inv_stockout_risk = 0.75

            # Weather parameters (use override or defaults)
            weather = weather_override or {}
            weather_sev = weather.get("severity", "minor")
            wind_speed = weather.get("wind_speed_kmh", 20.0)
            precip = weather.get("precipitation_mm", 0.0)

            # Raw operational feature dictionary
            raw_features: Dict[str, Any] = {
                "route_distance_nm": distance_nm,
                "weight_kg": shipment.weight_kg or 5000.0,
                "priority": shipment.priority.value if hasattr(shipment.priority, "value") else str(shipment.priority),
                "supplier_reliability": supplier.reliability_score if supplier else 0.80,
                "supplier_lead_time_days": supplier.lead_time_days if supplier else 14,
                "weather_severity": weather_sev,
                "wind_speed_kmh": wind_speed,
                "precipitation_mm": precip,
                "inventory_stockout_risk": inv_stockout_risk,
                "departure_month": float(datetime.now(timezone.utc).month),
                "departure_dow": float(datetime.now(timezone.utc).weekday()),
            }

            # 1. Evaluate prediction probability and composite risk
            risk_eval = self.predictor.evaluate_composite_risk(raw_features)

            # 2. Compute local SHAP explanation
            shap_eval = self.explainer.explain_raw_features(raw_features)

            prediction_record_id = None
            risk_record_id = None

            if persist:
                # Save ML Prediction record with SHAP explanation snapshot
                pred_rec = MLPredictionCRUD.create(
                    session,
                    model_name=self.predictor.MODEL_NAME,
                    model_version=self.predictor.MODEL_VERSION,
                    prediction_type="shipment_delay_probability",
                    entity_type="shipment",
                    entity_id=shipment.id,
                    predicted_value=risk_eval["ml_delay_probability"],
                    confidence=round(1.0 - abs(0.5 - risk_eval["ml_delay_probability"]) * 0.4, 3),
                    features_json=json.dumps(raw_features),
                    shap_values_json=json.dumps(shap_eval["attributions"]),
                )
                prediction_record_id = pred_rec.id

                # Save associated Composite Risk Assessment
                level_map = {
                    "CRITICAL": RiskLevel.CRITICAL,
                    "HIGH": RiskLevel.HIGH,
                    "MEDIUM": RiskLevel.MEDIUM,
                    "LOW": RiskLevel.LOW,
                }
                risk_rec = RiskCRUD.create(
                    session,
                    entity_type="shipment",
                    entity_id=shipment.id,
                    risk_category="ml_composite_delay_risk",
                    likelihood=risk_eval["ml_delay_probability"],
                    impact=round(min(1.0, risk_eval["composite_risk_score"] * 1.15), 3),
                    risk_score=risk_eval["composite_risk_score"],
                    risk_level=level_map.get(risk_eval["risk_classification"], RiskLevel.MEDIUM),
                    description=f"ML Composite delay risk evaluated at {risk_eval['composite_risk_score']}",
                    assessed_by=f"{self.predictor.MODEL_NAME}_v{self.predictor.MODEL_VERSION}",
                )
                risk_record_id = risk_rec.id

            return {
                "shipment_id": shipment.id,
                "tracking_id": shipment.tracking_id,
                "ml_delay_probability": risk_eval["ml_delay_probability"],
                "composite_risk_score": risk_eval["composite_risk_score"],
                "risk_classification": risk_eval["risk_classification"],
                "risk_breakdown": risk_eval["risk_breakdown"],
                "shap_explanation": shap_eval,
                "features_snapshot": raw_features,
                "persisted_prediction_id": prediction_record_id,
                "persisted_risk_assessment_id": risk_record_id,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            }

    def get_prediction_history(
        self,
        entity_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve prediction and SHAP explanation history from SQLite.
        """
        with self.db.session() as session:
            preds = MLPredictionCRUD.list_by_model(session, self.predictor.MODEL_NAME)
            if entity_id:
                preds = [p for p in preds if p.entity_id == entity_id]

            results = []
            for p in preds[:limit]:
                results.append({
                    "id": p.id,
                    "model_name": p.model_name,
                    "model_version": p.model_version,
                    "prediction_type": p.prediction_type,
                    "entity_id": p.entity_id,
                    "predicted_value": p.predicted_value,
                    "confidence": p.confidence,
                    "features": json.loads(p.features_json) if p.features_json else {},
                    "shap_values": json.loads(p.shap_values_json) if p.shap_values_json else {},
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                })
            return results
