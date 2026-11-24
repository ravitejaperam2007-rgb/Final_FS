"""
Unified model trainer — handles data splitting, fitting, checkpointing.
"""


class ModelTrainer:
    """Generic training loop wrapper."""

    def train(self, model, data, params: dict | None = None):
        raise NotImplementedError

    def save_checkpoint(self, model, path: str):
        raise NotImplementedError
