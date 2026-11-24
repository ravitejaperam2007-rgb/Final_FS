import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.environ["DISABLE_SQLALCHEMY_CEXT_RUNTIME"] = "1"

from database.connection import DatabaseManager
from database.models import (
    Shipment,
    ShipmentHistory,
    WeatherEvidence,
    MLPrediction,
    RiskAssessment,
    AgentExecution,
    ResiliencePlan,
    ApprovalHistory,
)

db = DatabaseManager()
with db.session() as s:
    print(f"Total Shipments: {s.query(Shipment).count()}")
    latest_shipment = s.query(Shipment).order_by(Shipment.id.desc()).first()
    if latest_shipment:
        print(f"  Latest Shipment: ID={latest_shipment.id}, Tracking={latest_shipment.tracking_id}, Status={latest_shipment.status.value}")
    
    print(f"Weather Evidence Count: {s.query(WeatherEvidence).count()}")
    latest_weath = s.query(WeatherEvidence).order_by(WeatherEvidence.id.desc()).first()
    if latest_weath:
        print(f"  Latest Weather: ID={latest_weath.id}, Severity={latest_weath.severity.value}, Temp={latest_weath.temperature_celsius}C, Wind={latest_weath.wind_speed_kmh}km/h")
        
    print(f"ML Predictions Count: {s.query(MLPrediction).count()}")
    latest_pred = s.query(MLPrediction).order_by(MLPrediction.id.desc()).first()
    if latest_pred:
        print(f"  Latest Prediction: ID={latest_pred.id}, Prob={latest_pred.predicted_value:.3f}")
        
    print(f"Risk Assessments Count: {s.query(RiskAssessment).count()}")
    latest_risk = s.query(RiskAssessment).order_by(RiskAssessment.id.desc()).first()
    if latest_risk:
        print(f"  Latest Risk Assessment: ID={latest_risk.id}, Score={latest_risk.risk_score:.2f}, Level={latest_risk.risk_level.name}")
        
    print(f"Agent Executions Count: {s.query(AgentExecution).count()}")
    recent_agents = s.query(AgentExecution).order_by(AgentExecution.id.desc()).limit(7).all()
    for a in reversed(recent_agents):
        print(f"  Agent: {a.agent_name:<30} Status={a.status.value:<10} Duration={a.duration_ms or 0}ms")
        
    print(f"Resilience Plans Count: {s.query(ResiliencePlan).count()}")
    latest_plans = s.query(ResiliencePlan).order_by(ResiliencePlan.id.desc()).limit(3).all()
    for p in latest_plans:
        print(f"  Plan #{p.id}: {p.name:<35} Status={p.status.value}")
        
    print(f"Approval History Count: {s.query(ApprovalHistory).count()}")
    latest_app = s.query(ApprovalHistory).order_by(ApprovalHistory.id.desc()).first()
    if latest_app:
        act = latest_app.action.value if hasattr(latest_app.action, "value") else str(latest_app.action)
        print(f"  Latest Approval: Action={act}, Approver={latest_app.approved_by}, Notes='{latest_app.comments}'")
