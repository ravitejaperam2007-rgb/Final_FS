"""
AWARE-AI Comprehensive Performance Benchmark and Profiling Suite.
Measures latency, throughput, cache hit ratios, and identifies optimization targets.
"""

import os
import sys
import time
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.environ["DISABLE_SQLALCHEMY_CEXT_RUNTIME"] = "1"

from database.connection import DatabaseManager
from database.crud import ShipmentCRUD, PortCRUD, SupplierCRUD, InventoryCRUD
from database.models import Shipment, RiskAssessment, WeatherEvidence, MLPrediction, AgentExecution
from ml.pipelines.pipeline_engine import MLExplainabilityPipeline
from agents.orchestrator import AgentOrchestrator
from modules.weather.api_client import WeatherAPIClient
from modules.inventory.optimizer import InventoryOptimizer


def benchmark_database(db: DatabaseManager, iterations=100):
    print("\n--- 1. Database Query & Transaction Latency (SQLite WAL) ---")
    start = time.perf_counter()
    with db.session() as s:
        for _ in range(iterations):
            _ = s.query(Shipment).all()
    duration = time.perf_counter() - start
    avg_ms = (duration / iterations) * 1000
    print(f"  • Fleet Read Query (Shipments): {avg_ms:.2f} ms / query ({iterations / duration:.1f} queries/sec)")
    
    # Measure point lookup
    start = time.perf_counter()
    with db.session() as s:
        for _ in range(iterations):
            _ = ShipmentCRUD.get(s, 1)
    duration = time.perf_counter() - start
    avg_lookup_ms = (duration / iterations) * 1000
    print(f"  • Point Lookup (Shipment by PK): {avg_lookup_ms:.3f} ms / query ({iterations / duration:.1f} lookups/sec)")
    
    return {"fleet_query_ms": avg_ms, "point_lookup_ms": avg_lookup_ms}


def benchmark_ml_and_shap(db: DatabaseManager, iterations=10):
    print("\n--- 2. ML Inference & TreeSHAP Attribution Latency ---")
    pipeline = MLExplainabilityPipeline(db_manager=db)
    
    # Warmup
    _ = pipeline.predict_and_explain_shipment(1, persist=False)
    
    start = time.perf_counter()
    for _ in range(iterations):
        _ = pipeline.predict_and_explain_shipment(1, persist=False)
    duration = time.perf_counter() - start
    avg_ms = (duration / iterations) * 1000
    print(f"  • Full LightGBM Prediction + TreeSHAP Explanation: {avg_ms:.2f} ms / inference")
    
    # Raw predictor latency
    dummy_feat = {
        "route_distance_nm": 1200.0,
        "weight_kg": 5000.0,
        "priority": "high",
        "supplier_reliability": 0.85,
        "supplier_lead_time_days": 12,
        "weather_severity": "moderate",
        "wind_speed_kmh": 25.0,
        "precipitation_mm": 5.0,
        "inventory_stockout_risk": 0.2,
        "departure_month": 11.0,
        "departure_dow": 2.0,
    }
    start = time.perf_counter()
    for _ in range(iterations * 10):
        _ = pipeline.predictor.evaluate_composite_risk(dummy_feat)
    raw_duration = time.perf_counter() - start
    avg_raw_ms = (raw_duration / (iterations * 10)) * 1000
    print(f"  • Feature Transform + LightGBM + Composite Risk: {avg_raw_ms:.3f} ms / call")
    
    return {"full_ml_shap_ms": avg_ms, "raw_booster_ms": avg_raw_ms}


def benchmark_weather_caching(db: DatabaseManager):
    print("\n--- 3. Weather API & TTL Cache Latency ---")
    client = WeatherAPIClient(cache_ttl_seconds=3600)
    
    # 1. Warm cache hit
    client.get_current_weather(31.2304, 121.4737)  # Warm
    start = time.perf_counter()
    for _ in range(50):
        _ = client.get_current_weather(31.2304, 121.4737)
    duration = time.perf_counter() - start
    cached_ms = (duration / 50) * 1000
    print(f"  • Cached Weather Retrieval (TTL Hit): {cached_ms:.4f} ms / call ({50 / duration:,.0f} req/sec)")
    
    return {"cached_weather_ms": cached_ms}


def benchmark_agent_swarm(db: DatabaseManager, iterations=3):
    print("\n--- 4. Multi-Agent Swarm Orchestration Latency ---")
    orchestrator = AgentOrchestrator(db_manager=db)
    
    times = []
    for i in range(iterations):
        start = time.perf_counter()
        res = orchestrator.run_shipment_intelligence_cycle(1)
        dur = (time.perf_counter() - start) * 1000
        times.append(dur)
        print(f"  • Cycle #{i+1}: {dur:.1f} ms (Cycle Status: {res.get('cycle_status')})")
        
    avg_swarm_ms = sum(times) / len(times)
    print(f"  • Average 7-Agent Swarm Cycle: {avg_swarm_ms:.1f} ms")
    
    return {"avg_swarm_cycle_ms": avg_swarm_ms}


def main():
    print("=================================================================")
    print("AWARE-AI SYSTEM PERFORMANCE PROFILING & BENCHMARK")
    print("=================================================================")
    
    db = DatabaseManager()
    db.init()
    
    db_metrics = benchmark_database(db)
    ml_metrics = benchmark_ml_and_shap(db)
    weather_metrics = benchmark_weather_caching(db)
    swarm_metrics = benchmark_agent_swarm(db)
    
    summary = {
        "database": db_metrics,
        "machine_learning": ml_metrics,
        "weather_cache": weather_metrics,
        "multi_agent_swarm": swarm_metrics,
    }
    
    report_file = ROOT_DIR / "docs" / "performance_profile.json"
    with open(report_file, "w") as f:
        json.dump(summary, f, indent=2)
        
    print("\n=================================================================")
    print(f"Performance report saved to: {report_file}")
    print("=================================================================")


if __name__ == "__main__":
    main()
