"""
Weather alert generation and notification dispatch.
"""


class WeatherAlertService:
    """Generate and dispatch weather alerts."""

    def check_alerts(self, location: str):
        raise NotImplementedError

    def send_notification(self, alert: dict):
        raise NotImplementedError
