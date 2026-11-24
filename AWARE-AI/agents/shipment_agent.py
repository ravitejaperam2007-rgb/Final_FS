"""
ShipmentAgent — Monitors and manages shipment-related decisions.
"""

from .base_agent import BaseAgent


class ShipmentAgent(BaseAgent):
    """Monitors and manages shipment-related decisions."""

    def perceive(self, context: dict) -> dict:
        raise NotImplementedError

    def decide(self, perception: dict) -> dict:
        raise NotImplementedError

    def act(self, decision: dict) -> dict:
        raise NotImplementedError
