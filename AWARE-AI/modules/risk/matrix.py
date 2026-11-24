"""
Risk matrix — likelihood × impact grid for visualisation.
"""


class RiskMatrix:
    """Build a likelihood-impact risk matrix."""

    def build(self, risks: list[dict]) -> dict:
        raise NotImplementedError
