"""
Comprehensive Unit & Integration Tests for AWARE-AI Machine Learning & SHAP Engine.

Tests:
1. Feature pipeline transformation and schema enforcement.
2. LightGBM delay probability prediction and boundary constraints.
3. Composite risk index calculation (separating ML probability from operational risk).
4. SHAP TreeExplainer feature attributions and global gain ranking.
5. End-to-end ML prediction & explanation pipeline with SQLite persistence.
6. History retrieval of past predictions and SHAP attributions.
"""

import pytest

from database.crud import MLPredictionCRUD, PortCRUD, RiskCRUD, ShipmentCRUD, SupplierCRUD
from ml.explainability.shap_explainer import ShapExplainer
from ml.models.risk_predictor import ShipmentDelayPredictor
from ml.pipelines.pipeline import FEATURE_NAMES, ShipmentFeaturePipeline
from ml.pipelines.pipeline_engine import MLExplainabilityPipeline


class TestShipmentFeaturePipeline:
    def test_pipeline_transforms_single_raw_dict(self):
        raw = {
            "route_distance_nm": 3500.0,
            "weight_kg": 12000.0,
            "priority": "high",
            "supplier_reliability": 0.92,
            "supplier_lead_time_days": 18,
            "weather_severity": "severe",
            "wind_speed_kmh": 65.0,
            "precipitation_mm": 22.0,
            "inventory_stockout_risk": 0.45,
            "departure_month": 11,
            "departure_dow": 4,
        }
        df = ShipmentFeaturePipeline.transform_single(raw)
        assert list(df.columns) == FEATURE_NAMES
        assert df["priority_level"].iloc[0] == 3.0  # high
        assert df["weather_severity_code"].iloc[0] == 2.0  # severe
        assert df["supplier_reliability"].iloc[0] == 0.92

    def test_pipeline_clamps_out_of_bounds_inputs(self):
        raw = {
            "supplier_reliability": 1.5,
            "inventory_stockout_risk": -0.2,
            "departure_month": 15,
        }
        df = ShipmentFeaturePipeline.transform_single(raw)
        assert df["supplier_reliability"].iloc[0] == 1.0
        assert df["inventory_stockout_risk"].iloc[0] == 0.0
        assert df["departure_month"].iloc[0] == 12.0


class TestLightGBMDelayPredictor:
    @pytest.fixture(scope="class")
    def predictor(self):
        p = ShipmentDelayPredictor()
        p.train_baseline_model(random_state=42)
        return p

    def test_predict_delay_probability_bounds(self, predictor):
        raw = {
            "route_distance_nm": 5000.0,
            "weight_kg": 20000.0,
            "priority": "critical",
            "supplier_reliability": 0.40,
            "supplier_lead_time_days": 45,
            "weather_severity": "extreme",
            "wind_speed_kmh": 95.0,
            "precipitation_mm": 40.0,
            "inventory_stockout_risk": 0.90,
        }
        df = ShipmentFeaturePipeline.transform_single(raw)
        prob = predictor.predict_delay_probability(df)

        assert 0.0 <= prob <= 1.0
        # Given extreme weather and low supplier reliability, delay prob should be elevated
        assert prob > 0.40

    def test_composite_risk_scoring_separation(self, predictor):
        raw = {
            "route_distance_nm": 800.0,
            "supplier_reliability": 0.95,
            "weather_severity": "minor",
            "wind_speed_kmh": 12.0,
            "inventory_stockout_risk": 0.10,
        }
        result = predictor.evaluate_composite_risk(raw)

        # ML probability must be reported separately from composite risk
        assert "ml_delay_probability" in result
        assert "composite_risk_score" in result
        assert "risk_classification" in result
        assert "risk_breakdown" in result

        assert 0.0 <= result["ml_delay_probability"] <= 1.0
        assert 0.0 <= result["composite_risk_score"] <= 1.0
        assert result["risk_classification"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


class TestShapExplainability:
    @pytest.fixture(scope="class")
    def explainer(self):
        return ShapExplainer()

    def test_instance_explanation(self, explainer):
        raw = {
            "route_distance_nm": 4500.0,
            "weather_severity": "severe",
            "wind_speed_kmh": 80.0,
            "supplier_reliability": 0.55,
        }
        explanation = explainer.explain_raw_features(raw)

        assert "base_value" in explanation
        assert "attributions" in explanation
        assert len(explanation["attributions"]) == len(FEATURE_NAMES)
        assert "top_positive_drivers" in explanation
        assert len(explanation["top_positive_drivers"]) > 0

    def test_global_feature_importance(self, explainer):
        importance = explainer.get_global_feature_importance()
        assert len(importance) == len(FEATURE_NAMES)
        total_pct = sum(item["importance_pct"] for item in importance)
        assert pytest.approx(100.0, abs=1.0) == total_pct


class TestMLExplainabilityPipeline:
    def test_end_to_end_prediction_explanation_and_persistence(self, db):
        # 1. Setup base database records
        with db.session() as s:
            p1 = PortCRUD.create(s, name="Shenzhen", code="CNSZX", country="China", latitude=22.54, longitude=114.05)
            p2 = PortCRUD.create(s, name="Long Beach", code="USLGB", country="USA", latitude=33.77, longitude=-118.19)
            sup = SupplierCRUD.create(s, name="Global Micro", country="China", reliability_score=0.72)
            shipment = ShipmentCRUD.create(
                s, tracking_id="ML-SHIP-01", origin_port_id=p1.id, destination_port_id=p2.id,
                supplier_id=sup.id, priority="high", weight_kg=15000.0,
            )
            ship_id = shipment.id

        pipeline = MLExplainabilityPipeline(db_manager=db)

        # 2. Predict and Explain
        eval_res = pipeline.predict_and_explain_shipment(
            ship_id,
            weather_override={"severity": "severe", "wind_speed_kmh": 75.0, "precipitation_mm": 30.0},
            persist=True,
        )

        assert eval_res["shipment_id"] == ship_id
        assert "ml_delay_probability" in eval_res
        assert "composite_risk_score" in eval_res
        assert "shap_explanation" in eval_res
        assert eval_res["persisted_prediction_id"] is not None
        assert eval_res["persisted_risk_assessment_id"] is not None

        # 3. Verify MLPrediction database record
        with db.session() as s:
            pred_db = MLPredictionCRUD.get(s, eval_res["persisted_prediction_id"])
            assert pred_db is not None
            assert pred_db.prediction_type == "shipment_delay_probability"
            assert pred_db.predicted_value == eval_res["ml_delay_probability"]
            assert pred_db.shap_values_json is not None

            # Verify associated RiskAssessment record
            risk_db = RiskCRUD.get(s, eval_res["persisted_risk_assessment_id"])
            assert risk_db is not None
            assert risk_db.risk_score == eval_res["composite_risk_score"]

        # 4. Verify History Retrieval
        history = pipeline.get_prediction_history(entity_id=ship_id)
        assert len(history) == 1
        assert history[0]["entity_id"] == ship_id
        assert len(history[0]["shap_values"]) == len(FEATURE_NAMES)
