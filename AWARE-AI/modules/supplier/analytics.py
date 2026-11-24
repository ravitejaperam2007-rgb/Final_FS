"""
Supplier analytics — trend analysis, spend breakdown, lead-time stats.
"""


class SupplierAnalytics:
    """Descriptive and diagnostic analytics for suppliers."""

    def lead_time_distribution(self, supplier_id: str):
        raise NotImplementedError

    def spend_breakdown(self, supplier_id: str):
        raise NotImplementedError
