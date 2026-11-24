"""
Demand forecasting — time-series predictions for inventory planning.
"""


class DemandForecaster:
    """Predict future demand for SKUs."""

    def forecast(self, sku: str, horizon_days: int = 30):
        raise NotImplementedError
