# AWARE-AI Architecture

## High-Level Overview

AWARE-AI is a modular, AI-driven supply-chain risk management platform.

### Core Layers

1. **Frontend** — Streamlit multi-page dashboard (`app/`)
2. **Intelligence Modules** — domain-specific logic (`modules/`)
3. **Machine Learning** — predictive models & SHAP explainability (`ml/`)
4. **Multi-Agent System** — autonomous decision agents (`agents/`)
5. **Database** — persistence and ORM (`database/`)
6. **Utilities** — logging, validation, helpers (`utils/`)

## Data Flow

```
Weather APIs ──┐
Supplier Data ─┤
Shipment Data ─┼──▶ Intelligence Modules ──▶ ML Pipeline ──▶ Agent Orchestrator
Inventory Data ┘                                               │
                                                               ▼
                                                        Streamlit Dashboard
```
