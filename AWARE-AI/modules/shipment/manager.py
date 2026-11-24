"""
Shipment lifecycle management — creation, updates, status transitions.
"""


class ShipmentManager:
    """Manages shipment CRUD and state machine."""

    def create_shipment(self, **kwargs):
        raise NotImplementedError

    def update_status(self, shipment_id: str, status: str):
        raise NotImplementedError

    def get_shipment(self, shipment_id: str):
        raise NotImplementedError
