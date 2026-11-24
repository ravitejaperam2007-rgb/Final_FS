# ⚓ AWARE-AI: Autonomous Supply Chain Risk & Resilience Control Tower

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Database: SQLite WAL](https://img.shields.io/badge/database-SQLite%20WAL-success.svg)](https://www.sqlite.org/wal.html)
[![ML: LightGBM](https://img.shields.io/badge/ML-LightGBM-brightgreen.svg)](https://lightgbm.readthedocs.io/)
[![Explainability: TreeSHAP](https://img.shields.io/badge/Explainability-TreeSHAP-orange.svg)](https://shap.readthedocs.io/)
[![Multi-Agent: 7 Specialized](https://img.shields.io/badge/Multi--Agent-7%20Specialized%20Agents-blueviolet.svg)](https://github.com/)
[![Tests: 166 Passed](https://img.shields.io/badge/tests-166%20passed-green.svg)](docs/FINAL_TEST_REPORT.md)

**AWARE-AI** is an enterprise-grade autonomous supply chain risk prediction, root-cause diagnosis, and resilience planning control tower. It bridges operational multi-echelon supply chain management with gradient-boosted machine learning, TreeSHAP local explainability, and a 7-agent coordinated AI swarm to safeguard global maritime freight corridors from disruption.

---

## 1. Project Objectives

Global supply chains face high-frequency compounding vulnerabilities: severe maritime weather squalls, supplier delivery volatility, demurrage penalties, and downstream manufacturing line stoppages. 

AWARE-AI solves these challenges by providing:
1. **End-to-End Visibility:** Continuous tracking of maritime consignments, international ports, inventory buffers, and vendor reliability.
2. **Transparent ML Predictions:** Calibrated LightGBM delay probability prediction decoupled from operational risk.
3. **Local Explainability:** TreeSHAP exact additive feature attribution explaining *why* a shipment is at risk without black-box opacity.
4. **Autonomous Agent Swarm:** 7 specialized agents operating in an auditable perceive $\to$ decide $\to$ act lifecycle to diagnose root causes and financial exposure.
5. **Human-Governed Resilience Planning:** Candidate maritime recovery playbooks with multi-criteria trade-off scoring and mandatory Human-in-the-Loop review before operational changes.

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Data Layer ["Data & Persistence Layer"]
        DB[(SQLite WAL Engine)]
        Ports[Ports & Maritime Geodetics]
        Suppliers[Strategic Supplier Profiles]
        Inventory[Inventory SKUs & EOQ]
        Shipments[Shipments & Audit Ledger]
        WeatherDB[Weather Evidence]
    end

    subgraph Operational Intelligence ["Operational Intelligence Modules"]
        OM[Open-Meteo REST API Client]
        SS[Empirical Supplier Scorer]
        IO[Wilson EOQ & Safety Buffer Optimizer]
        GC[Great-Circle Route Geodetics]
    end

    subgraph ML & Explainability ["Machine Learning & Explainability"]
        FP[11-Feature Canonical Pipeline]
        LGBM[LightGBM Delay Predictor]
        SHAP[TreeSHAP Exact Attributions]
        CR[Composite Risk Index Engine]
    end

    subgraph Multi-Agent Swarm ["7 Specialized Autonomous Agents"]
        ORCH[Agent Orchestrator]
        A1[Weather Intelligence Agent]
        A2[Supplier Intelligence Agent]
        A3[Risk Assessment Agent]
        A4[Root Cause Analysis Agent]
        A5[Impact Assessment Agent]
        A6[Mitigation Recommendation Agent]
        A7[Resilience Planning Agent]
    end

    subgraph Resilience & Governance ["Resilience & Governance"]
        MR[Maritime Route Deviation Engine]
        BIA[Financial Demurrage & Line Stoppage Engine]
        ARP[Autonomous Resilience Planner]
        HITL[Human Approval Workflow Manager]
    end

    subgraph UI Control Tower ["Streamlit Enterprise UI (9 Modules)"]
        UI1[1. Global Control Tower]
        UI2[2. Shipment Management]
        UI3[3. Shipment Risk Analysis]
        UI4[4. Multi-Agent Center]
        UI5[5. Root Cause & Impact]
        UI6[6. Resilience Planning]
        UI7[7. Weather & Maritime]
        UI8[8. Supplier & Inventory]
        UI9[9. System Monitoring]
    end

    Data Layer --> Operational Intelligence
    Operational Intelligence --> ML & Explainability
    ML & Explainability --> Multi-Agent Swarm
    Multi-Agent Swarm --> Resilience & Governance
    Resilience & Governance --> UI Control Tower
    HITL -.->|Approval Audit| DB
```

---

## 3. Technology Stack

| Domain | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.10 / 3.11 / 3.12 / 3.13 | Core runtime environment. |
| **Frontend** | Streamlit, Plotly, Altair | Dark-themed enterprise supply chain control tower. |
| **Database** | SQLite 3, SQLAlchemy 2.0, Alembic | WAL journal mode, busy timeouts (5000ms), FK cascade enforcement. |
| **Machine Learning** | LightGBM, Scikit-Learn | Binary delay probability classifier ($[0.0, 1.0]$). |
| **Explainability** | TreeSHAP | Instance-level local feature attribution and global feature gain. |
| **Weather API** | Open-Meteo REST API | Real-time atmospheric marine conditions with TTL in-memory caching. |
| **Testing** | Pytest, Pytest-Asyncio | 166 unit, scenario, and UI integration tests. |
| **Containerization** | Docker, Docker-Compose | Reproducible containerized deployment on Linux/Debian slim. |

---

## 4. Machine Learning & TreeSHAP Methodology

### Feature Pipeline
The pipeline transforms 11 canonical operational features without data leakage:
1. `route_distance_nm`: Great-Circle distance computed via the Haversine formula.
2. `weight_kg`: Consignment gross weight.
3. `priority_level`: Ordinal priority (`low`=1, `medium`=2, `high`=3, `critical`=4).
4. `supplier_reliability`: Empirical supplier score $[0.0, 1.0]$.
5. `supplier_lead_time_days`: Baseline vendor delivery lead-time.
6. `weather_severity_code`: Numerical hazard code (`minor`=0, `moderate`=1, `severe`=2, `extreme`=3).
7. `wind_speed_kmh`: Prevailing atmospheric wind speed.
8. `precipitation_mm`: Total precipitation volume.
9. `inventory_stockout_risk`: Downstream SKU buffer deficit indicator $[0.0, 1.0]$.
10. `departure_month`: Cyclical seasonal factor.
11. `departure_dow`: Day of week factor.

### TreeSHAP Local Attributions
Unlike black-box models, AWARE-AI decomposes every individual prediction via TreeSHAP into additive feature contributions:
$$\text{Log-Odds Prediction} = \phi_0 + \sum_{i=1}^{M} \phi_i$$
Positive $\phi_i$ values (rendered in red) illustrate drivers increasing delay probability; negative $\phi_i$ values (in blue) show stabilizing factors.

---

## 5. Composite Risk Methodology

AWARE-AI enforces strict separation between the statistical **ML delay probability** ($P_{\text{delay}}$) and the operational **composite risk index** ($R_{\text{composite}}$):
- **ML Delay Probability:** The pure statistical likelihood that a vessel arrives behind schedule.
- **Composite Risk Score ($0.0 - 1.0$):** Multi-factor weighted index aggregating:
  - Predictive ML likelihood ($35\%$)
  - Environmental weather hazard severity ($25\%$)
  - Empirical vendor reliability deficit ($20\%$)
  - Downstream inventory stockout criticality ($20\%$)

**Risk Classification Tiers:**
- `LOW` ($0.00 \le R < 0.35$): Routine transit; standard monitoring.
- `MEDIUM` ($0.35 \le R < 0.65$): Elevated corridor delay likelihood; heightened tracking.
- `HIGH` ($0.65 \le R < 0.85$): Actionable disruption warning; candidate playbook synthesis triggered.
- `CRITICAL` ($0.85 \le R \le 1.00$): Urgent assembly threat; immediate executive intervention required.

---

## 6. Multi-Agent AI Workflow

The 7 specialized agents execute a structured sequence coordinated by the `AgentOrchestrator`:

1. **Weather Intelligence Agent:** Monitors marine atmospheric conditions and records `WeatherEvidence`.
2. **Supplier Intelligence Agent:** Assesses empirical vendor performance, volatility, and delay rates.
3. **Risk Assessment Agent:** Combines ML probability with multi-factor risk scores and writes `RiskAssessment`.
4. **Root Cause Analysis Agent:** Translates TreeSHAP local attributions and domain thresholds into causal categories (`WEATHER`, `SUPPLIER`, `PORT_CONGESTION`).
5. **Impact Assessment Agent:** Quantifies holding costs, demurrage ($1,500/day), contract SLA penalties, and line stoppage liabilities ($8,000/hr).
6. **Mitigation Recommendation Agent:** Generates operational mitigations (contingency bunkers, priority berthing, dual-sourcing).
7. **Resilience Planning Agent:** Evaluates alternative maritime routes, scores candidate playbooks, and persists `DRAFT` plans.

---

## 7. Resilience Planning & Human Governance

AWARE-AI strictly prohibits autonomous changes to live operational consignments. 
- Candidate recovery playbooks are generated in `DRAFT` status.
- Candidate plans are compared side-by-side using a multi-objective utility formula:
  $$\text{Utility} = 0.40 \times \Delta R + 0.35 \times \text{Savings Score} + 0.25 \times \text{Feasibility}$$
- A human operator (Logistics Director / Dispatcher) must review and record a formal decision (`approve`, `reject`, `revise`).
- All decisions are recorded in the immutable `ApprovalHistory` ledger.

---

## 8. Deployment & Quick Start

### Option A: Local Installation (Python 3.10+)

1. **Clone repository and configure environment:**
   ```bash
   cd AWARE-AI
   cp .env.example .env
   ```

2. **Create virtual environment & install requirements:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Initialize database schema & seed demonstration data:**
   ```bash
   python main.py init-db
   python main.py seed-db
   ```

4. **Launch Streamlit Control Tower:**
   ```bash
   python main.py run
   ```
   Access the dashboard at `http://localhost:8501`.

---

### Option B: Docker Container Deployment

1. **Build and run via Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

2. **Verify container health:**
   ```bash
   docker ps
   curl -f http://localhost:8501/_stcore/health
   ```

3. **Initialize & seed data inside container:**
   ```bash
   docker exec -it aware_ai_control_tower python main.py init-db
   docker exec -it aware_ai_control_tower python main.py seed-db
   ```

---

## 9. Testing & Verification Results

The entire codebase is verified through 166 automated unit and integration tests.

```powershell
python main.py test
```

**Verification Results Summary:**
- **Total Tests:** 166 passed (0 failures, 0 skipped).
- **Test Categories:**
  - `test_database/`: Schema migrations, SQLite WAL pragmas, CRUD cascades, relational constraints.
  - `test_weather/`: Open-Meteo REST client, TTL caching, fallback handling.
  - `test_supplier/`: Empirical reliability scoring, lead-time volatility, dual-sourcing.
  - `test_inventory/`: Multi-tier criticality, safety stock deficit detection, Wilson EOQ.
  - `test_ml/`: LightGBM classifier calibration, TreeSHAP feature attributions.
  - `test_agents/`: 7 individual agents and full multi-agent orchestration cycle.
  - `test_resilience/`: Alternative maritime routing, financial exposure, Human-in-the-Loop approval.
  - `test_end_to_end_scenario.py`: Super Typhoon maritime disruption lifecycle.
  - `test_ui_actions.py`: Automated interaction testing for all 9 Streamlit pages.

For the exhaustive test trace, see [FINAL_TEST_REPORT.md](docs/FINAL_TEST_REPORT.md).

---

## 10. Honest Limitations & Operational Scope

1. **Open-Meteo Rate Limits & Offline Fallbacks:** Open-Meteo standard non-commercial REST API does not require an API key but has rate limits. In offline or air-gapped container environments, the client automatically defaults to cached or synthetic fallback provenance.
2. **Simplified Maritime Geodesics:** Route distance calculations utilize spherical Great-Circle interpolation (Haversine formula). While diversion routes account for major shipping straits, exact bathymetric depth constraints and localized canal tolls (e.g. Suez/Panama) rely on standard proxy valuations.
3. **Simulated Financial Parameters:** Demurrage ($1,500/day) and assembly line downtime penalties ($8,000/hr) reflect standard automotive enterprise averages. These should be customized in production via `.env` to match company-specific carrier master contracts.
4. **Single-Node SQLite Concurrency:** SQLite in WAL mode reliably handles high-volume concurrent reads with serialized writes. For multi-region enterprise deployments with thousands of concurrent dispatchers, migrate `DATABASE_URL` to PostgreSQL.
