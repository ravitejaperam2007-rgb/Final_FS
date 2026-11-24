"""
SHAP visualisation helpers — summary plots, waterfall, force plots.
"""


class ShapVisualizer:
    """Generate SHAP visualisation artifacts."""

    def summary_plot(self, shap_values):
        raise NotImplementedError

    def waterfall_plot(self, shap_values, instance_idx: int = 0):
        raise NotImplementedError

    def force_plot(self, shap_values, instance_idx: int = 0):
        raise NotImplementedError
