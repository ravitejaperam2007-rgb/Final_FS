"""
Risk scoring — numeric risk quantification and categorisation.
"""


class RiskScorer:
    """Assign numeric risk scores to entities and routes."""

    def score(self, entity_type: str, entity_id: str) -> float:
        raise NotImplementedError

    def categorise(self, score: float) -> str:
        raise NotImplementedError
