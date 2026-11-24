"""
Risk assessment engine — aggregate risk from multiple sources.
"""


class RiskAssessment:
    """Evaluate overall supply-chain risk."""

    def assess(self, context: dict) -> dict:
        raise NotImplementedError
