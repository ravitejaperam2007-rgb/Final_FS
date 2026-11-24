"""
Pre-defined resilience strategies (dual-sourcing, buffer stock, re-routing).
"""


class StrategyLibrary:
    """Catalogue of resilience strategies."""

    def list_strategies(self) -> list[str]:
        raise NotImplementedError

    def recommend(self, risk_type: str) -> list[str]:
        raise NotImplementedError
