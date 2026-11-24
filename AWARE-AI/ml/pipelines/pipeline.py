"""
AWARE-AI — Machine Learning Feature Pipeline for Shipment Delay Prediction

Transforms operational shipment state, weather evidence, supplier reliability,
and route distance into a strictly validated, non-leaking feature vector.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


# Canonical feature schema required by the LightGBM delay predictor
FEATURE_NAMES: List[str] = [
    "route_distance_nm",
    "weight_kg",
    "priority_level",          # 1: Low, 2: Medium, 3: High, 4: Critical
    "supplier_reliability",    # 0.0 to 1.0
    "supplier_lead_time_days", # integer days
    "weather_severity_code",   # 0: Minor, 1: Moderate, 2: Severe, 3: Extreme
    "wind_speed_kmh",          # float
    "precipitation_mm",        # float
    "inventory_stockout_risk", # 0.0 to 1.0 (downstream inventory urgency)
    "departure_month",         # 1 to 12 (seasonality)
    "departure_dow",           # 0 to 6 (day of week)
]


class ShipmentFeaturePipeline:
    """
    Feature transformation pipeline for live shipment operational features.
    Guarantees no target leakage and strict schema compliance.
    """

    @classmethod
    def transform_single(cls, raw_features: Dict[str, Any]) -> pd.DataFrame:
        """
        Convert a raw feature dictionary into a 1-row DataFrame matching FEATURE_NAMES.
        """
        row = cls._extract_row(raw_features)
        df = pd.DataFrame([row], columns=FEATURE_NAMES)
        return df

    @classmethod
    def transform_batch(cls, records: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert a batch of raw feature dictionaries into a DataFrame.
        """
        rows = [cls._extract_row(r) for r in records]
        df = pd.DataFrame(rows, columns=FEATURE_NAMES)
        return df

    @classmethod
    def _extract_row(cls, data: Dict[str, Any]) -> Dict[str, float]:
        # Priority mapping
        prio_map = {"low": 1.0, "medium": 2.0, "high": 3.0, "critical": 4.0}
        priority_val = prio_map.get(str(data.get("priority", "medium")).lower(), 2.0)

        # Weather severity mapping
        sev_map = {"minor": 0.0, "moderate": 1.0, "severe": 2.0, "extreme": 3.0}
        sev_val = sev_map.get(str(data.get("weather_severity", "minor")).lower(), 0.0)

        # Distance
        distance = float(data.get("route_distance_nm", 1000.0))
        weight = float(data.get("weight_kg", 5000.0))
        sup_rel = float(data.get("supplier_reliability", 0.85))
        sup_lead = float(data.get("supplier_lead_time_days", 14.0))
        wind = float(data.get("wind_speed_kmh", 15.0))
        precip = float(data.get("precipitation_mm", 0.0))
        inv_risk = float(data.get("inventory_stockout_risk", 0.20))
        month = float(data.get("departure_month", 6.0))
        dow = float(data.get("departure_dow", 2.0))

        return {
            "route_distance_nm": max(10.0, distance),
            "weight_kg": max(1.0, weight),
            "priority_level": priority_val,
            "supplier_reliability": min(max(sup_rel, 0.0), 1.0),
            "supplier_lead_time_days": max(0.0, sup_lead),
            "weather_severity_code": sev_val,
            "wind_speed_kmh": max(0.0, wind),
            "precipitation_mm": max(0.0, precip),
            "inventory_stockout_risk": min(max(inv_risk, 0.0), 1.0),
            "departure_month": min(max(month, 1.0), 12.0),
            "departure_dow": min(max(dow, 0.0), 6.0),
        }
