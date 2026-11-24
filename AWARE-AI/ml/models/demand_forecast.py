"""
Demand forecasting model (e.g., Prophet, LSTM, XGBoost).
"""


class DemandForecastModel:
    """Train and predict demand."""

    def train(self, data):
        raise NotImplementedError

    def predict(self, horizon: int):
        raise NotImplementedError
