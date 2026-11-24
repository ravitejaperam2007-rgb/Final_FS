"""
Model evaluation — metrics computation, comparison reports.
"""


class ModelEvaluator:
    """Evaluate model performance against test data."""

    def evaluate(self, model, test_data) -> dict:
        raise NotImplementedError

    def compare(self, results: list[dict]) -> dict:
        raise NotImplementedError
