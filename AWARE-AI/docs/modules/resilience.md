# 🛡️ AWARE-AI Impact Assessment & Autonomous Resilience Planning

## Overview

The Resilience Planning and Impact Assessment system evaluates operational disruptions, calculates financial and inventory exposure, models maritime diversion corridors using geodesic calculations, compares candidate recovery strategies, and explains why an optimal plan is recommended.

> ⚠️ **Governance Rule**: All generated resilience plans remain in **`DRAFT`** status until explicitly reviewed and approved by a human authority via `HumanApprovalWorkflowManager`. No operational changes or routing updates are applied autonomously.

---

## 1. Architectural Workflow

```
                                [Shipment Operational Context]
                                              │
                 ┌────────────────────────────┴────────────────────────────┐
                 ▼                                                         ▼
    [MaritimeRouteEvaluator]                               [BusinessImpactAssessmentEngine]
     • Direct Great-Circle Route                            • Demurrage & detention costs
     • Intermediate Diversion Corridors                     • In-transit cargo holding costs
     • Real Geodesic Distances (NM)                         • Customer SLA breach exposure
     • Open-Meteo Corridor Weather                          • Manufacturing line stoppage risk
     • Transit Days & Bunker Costs                          • Downstream Inventory Vulnerability
                 │                                                         │
                 └────────────────────────────┬────────────────────────────┘
                                              ▼
                             [AutonomousResiliencePlanner]
                              • Plan A: Weather Corridor Deviation
                              • Plan B: Expedited Multi-Modal Split
                              • Plan C: Dual-Sourcing & Buffer Reallocation
                              • Side-by-side tradeoff matrix
                              • Multi-objective utility scoring
                              • Auditable recommendation reasoning
                                              │
                                              ▼ (Persisted as DRAFT in SQLite)
                            [HumanApprovalWorkflowManager]
                              • Human Review (approve / reject / revise)
                              • Immutable ApprovalHistory audit log
                              • State update: DRAFT -> ACTIVE / ARCHIVED
```

---

## 2. Component Details

### A. Alternative Maritime Route Evaluation (`modules/resilience/maritime_routes.py`)
- Evaluates great-circle routes using the Haversine formula on port coordinates.
- Assesses candidate transit diversion ports already registered in the SQLite database.
- Pulls live or cached Open-Meteo weather along each corridor.
- Computes transit days based on cruising speeds (nominal 18 knots) and estimated bunker fuel costs ($15,000/day).
- Flags operational feasibility (`HIGH`, `CAUTION`, `RESTRICTED`, `LOW_EFFICIENCY`).

### B. Business & Inventory Impact Engine (`modules/resilience/impact_engine.py`)
- **Demurrage & Detention**: $1,500/day container equivalent based on predicted delay duration.
- **In-Transit Holding Costs**: Assesses working capital lockup at 20% annual inventory holding cost.
- **SLA Breach Penalties**: Priority-tiered penalties ($5,000 to $15,000 base).
- **Line-Stoppage Risk**: Flags critical manufacturing assembly risks when shipments have `CRITICAL` priority or stockout vulnerability with delay probability $> 0.55$.

### C. Autonomous Resilience Planner (`modules/resilience/planner.py`)
- Formulates 3 candidate recovery playbooks tailored to root cause diagnoses.
- Evaluates expected risk reduction and calculates projected residual risk.
- **Multi-Objective Utility Ranking**:
  $$\text{Utility} = 0.40 \times (\text{Risk Reduction}) + 0.35 \times (\text{Net Financial Savings}) + 0.25 \times (\text{Operational Feasibility})$$
- Generates transparent, auditable natural language reasoning explaining the decision.

### D. Human-in-the-Loop Governance (`modules/resilience/approval_workflow.py`)
- Implements `review_and_decide(plan_id, action, approved_by, comments)`.
- Enforces human signoff before activating any plan in the database.
- Logs decisions into `ApprovalHistory`.

---

## 3. Usage Example

```python
from database.connection import DatabaseManager
from modules.resilience import AutonomousResiliencePlanner, HumanApprovalWorkflowManager

db = DatabaseManager()
planner = AutonomousResiliencePlanner(db)
workflow = HumanApprovalWorkflowManager(db)

# 1. Generate, evaluate, and compare recovery plans
evaluation = planner.generate_and_compare_plans(
    shipment_id=1,
    risk_profile={
        "ml_delay_probability": 0.75,
        "composite_risk_score": 0.68,
        "weather_severity": "severe",
    },
    persist_plans=True,
)

plan_id = evaluation["persisted_resilience_plan_id"]
print(f"Recommended Plan: {evaluation['recommended_plan']['name']}")
print(f"Reasoning: {evaluation['recommendation_reasoning']}")

# 2. Human Governance Signoff
decision = workflow.review_and_decide(
    plan_id=plan_id,
    action="approve",
    approved_by="Logistics Operations Director",
    comments="Approved maritime deviation corridor to bypass cyclone Gale.",
)
print(f"Plan Status: {decision['new_plan_status']}")
```
