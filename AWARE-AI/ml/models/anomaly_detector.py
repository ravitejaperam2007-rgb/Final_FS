"""
Anomaly detection model — flags unusual patterns in supply-chain data.
"""


class AnomalyDetectorModel:
    """Detect anomalies in time-series or tabular data."""

    def train(self, data):
        raise NotImplementedError

    def detect(self, data) -> list:
        raise NotImplementedError
