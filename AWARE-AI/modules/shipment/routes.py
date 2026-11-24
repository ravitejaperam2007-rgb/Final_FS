"""
AWARE-AI — Shipment Route & Geometric Calculation Helpers

Calculates:
- Great-circle distance (Haversine formula) in nautical miles and kilometers.
- Intermediate waypoint interpolation for en-route weather monitoring.
- Nominal transit time estimation under prevailing weather conditions.
"""

from __future__ import annotations

import math
from typing import List, Tuple


class RouteOptimizer:
    """
    Maritime & multimodal logistics distance and waypoint calculator.
    """

    EARTH_RADIUS_KM = 6371.0
    KM_TO_NM = 0.539957

    @classmethod
    def haversine_distance_km(
        cls,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate great circle distance between two points in kilometers.
        """
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(cls.EARTH_RADIUS_KM * c, 2)

    @classmethod
    def haversine_distance_nm(
        cls,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate distance in nautical miles.
        """
        km = cls.haversine_distance_km(lat1, lon1, lat2, lon2)
        return round(km * cls.KM_TO_NM, 2)

    @classmethod
    def interpolate_waypoints(
        cls,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
        num_waypoints: int = 3,
    ) -> List[Tuple[float, float]]:
        """
        Generate intermediate geodesic checkpoints between origin and destination.
        """
        waypoints = []
        for i in range(1, num_waypoints + 1):
            fraction = i / (num_waypoints + 1)
            # Linear spherical interpolation
            lat = lat1 + fraction * (lat2 - lat1)
            lon = lon1 + fraction * (lon2 - lon1)
            waypoints.append((round(lat, 4), round(lon, 4)))
        return waypoints
