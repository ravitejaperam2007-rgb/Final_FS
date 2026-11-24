"""
AWARE-AI — Open-Meteo Real-Time Weather API Client

Fetches live atmospheric conditions from the public Open-Meteo API.
Includes:
- TTL in-memory caching to respect rate limits and reduce latency.
- Comprehensive error handling with fallback to cached/historical values.
- Explicit data provenance flagging ('LIVE_API', 'CACHE', 'SYNTHETIC_FALLBACK', 'UNAVAILABLE').
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from utils.logger import get_logger

logger = get_logger("weather.api_client")

# Open-Meteo API WMO Weather Interpretation Codes
WMO_CODE_MAP: Dict[int, Tuple[str, str]] = {
    0: ("Clear sky", "minor"),
    1: ("Mainly clear", "minor"),
    2: ("Partly cloudy", "minor"),
    3: ("Overcast", "minor"),
    45: ("Fog", "moderate"),
    48: ("Depositing rime fog", "moderate"),
    51: ("Light drizzle", "minor"),
    53: ("Moderate drizzle", "minor"),
    55: ("Dense drizzle", "moderate"),
    61: ("Slight rain", "minor"),
    63: ("Moderate rain", "moderate"),
    65: ("Heavy rain", "severe"),
    71: ("Slight snow", "moderate"),
    73: ("Moderate snow", "moderate"),
    75: ("Heavy snow", "severe"),
    77: ("Snow grains", "moderate"),
    80: ("Slight rain showers", "minor"),
    81: ("Moderate rain showers", "moderate"),
    82: ("Violent rain showers", "severe"),
    85: ("Slight snow showers", "moderate"),
    86: ("Heavy snow showers", "severe"),
    95: ("Thunderstorm", "severe"),
    96: ("Thunderstorm with slight hail", "severe"),
    99: ("Thunderstorm with heavy hail", "extreme"),
}


class WeatherAPIClient:
    """
    Client for Open-Meteo REST API.
    Does not require an API key for standard non-commercial usage.
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, cache_ttl_seconds: int = 600, timeout: int = 5):
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout = timeout
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _cache_key(self, latitude: float, longitude: float) -> str:
        return f"{round(latitude, 4)}_{round(longitude, 4)}"

    def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Fetch real-time current weather for given coordinates.
        Returns a standardized dictionary with metadata and provenance tag.
        """
        key = self._cache_key(latitude, longitude)
        now_ts = time.time()

        # Check Cache
        if not force_refresh and key in self._cache:
            entry = self._cache[key]
            if now_ts - entry["cached_at_ts"] < self.cache_ttl_seconds:
                cached_data = dict(entry["data"])
                cached_data["data_source"] = "CACHE"
                cached_data["data_freshness_seconds"] = int(now_ts - entry["cached_at_ts"])
                return cached_data

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_gusts_10m",
            "timezone": "auto",
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "AWARE-AI-SupplyChainEngine/1.0"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))

            current = raw.get("current", {})
            w_code = current.get("weather_code", 0)
            condition_desc, severity = WMO_CODE_MAP.get(w_code, ("Unknown weather", "moderate"))

            # Calculate severe conditions from wind gusts or extreme rain
            wind_speed = current.get("wind_speed_10m", 0.0)
            precipitation = current.get("precipitation", 0.0)

            if wind_speed > 90.0 or precipitation > 50.0:
                severity = "extreme"
            elif wind_speed > 60.0 or precipitation > 25.0:
                severity = "severe"

            result = {
                "latitude": latitude,
                "longitude": longitude,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "data_source": "LIVE_API",
                "data_freshness_seconds": 0,
                "is_synthetic": False,
                "event_type": condition_desc,
                "severity": severity,
                "temperature_celsius": current.get("temperature_2m"),
                "relative_humidity": current.get("relative_humidity_2m"),
                "wind_speed_kmh": wind_speed,
                "wind_gusts_kmh": current.get("wind_gusts_10m"),
                "precipitation_mm": precipitation,
                "weather_code": w_code,
                "raw_payload": raw,
            }

            self._cache[key] = {
                "data": result,
                "cached_at_ts": now_ts,
            }
            return result

        except Exception as exc:
            logger.warning(
                "Open-Meteo API request failed for lat=%s, lon=%s: %s",
                latitude, longitude, exc
            )
            # If cached item exists, return it even if expired rather than failing completely
            if key in self._cache:
                entry = self._cache[key]
                stale_data = dict(entry["data"])
                stale_data["data_source"] = "EXPIRED_CACHE"
                stale_data["data_freshness_seconds"] = int(now_ts - entry["cached_at_ts"])
                stale_data["warning"] = f"Live fetch failed ({str(exc)}). Using stale cache."
                return stale_data

            # Explicit UNAVAILABLE result (not synthetic live data)
            return {
                "latitude": latitude,
                "longitude": longitude,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "data_source": "UNAVAILABLE",
                "data_freshness_seconds": None,
                "is_synthetic": False,
                "error": f"Network/API Error: {str(exc)}",
                "event_type": "Unavailable",
                "severity": "minor",
                "temperature_celsius": None,
                "wind_speed_kmh": None,
                "precipitation_mm": None,
                "raw_payload": None,
            }
