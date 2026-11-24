"""
InventoryAgent — Manages reorder triggers and stock-level alerts.
"""

from .base_agent import BaseAgent


class InventoryAgent(BaseAgent):
    """Manages reorder triggers and stock-level alerts."""

    def perceive(self, context: dict) -> dict:
        raise NotImplementedError

    def decide(self, perception: dict) -> dict:
        raise NotImplementedError

    def act(self, decision: dict) -> dict:
        raise NotImplementedError
