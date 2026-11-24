"""
AWARE-AI — Central Application & CLI Management Entry Point.

Usage:
  python main.py run           # Launch the Streamlit Control Tower application
  python main.py init-db       # Initialize the SQLite database schema
  python main.py seed-db       # Seed baseline global supply chain data
  python main.py train-model   # Train / retrain the LightGBM delay classification model
  python main.py test          # Run the test suite via pytest
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def run_app() -> None:
    """Launch the Streamlit Control Tower."""
    app_path = ROOT_DIR / "app" / "streamlit_app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    print(f"Launching AWARE-AI Control Tower: {' '.join(cmd)}")
    subprocess.run(cmd)


def init_db() -> None:
    """Initialize database tables idempotently."""
    from database.connection import DatabaseManager
    print("Initializing AWARE-AI SQLite database schema...")
    db = DatabaseManager()
    db.init()
    print("Schema initialized successfully.")


def seed_db() -> None:
    """Populate database with baseline international trade data."""
    from database.seed_data import seed_database
    seed_database()


def train_model() -> None:
    """Train or calibrate the LightGBM shipment delay model."""
    from ml.models.risk_predictor import ShipmentDelayPredictor
    print("Training / evaluating LightGBM delay prediction model...")
    predictor = ShipmentDelayPredictor()
    metrics = predictor.train()
    print(f"Model trained successfully! Metrics: {metrics}")


def run_tests() -> None:
    """Execute test suite."""
    print("Running AWARE-AI test suite...")
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    subprocess.run(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AWARE-AI: Autonomous Multi-Agent Supply Chain Control Tower",
    )
    parser.add_argument(
        "command",
        choices=["run", "init-db", "seed-db", "train-model", "test"],
        nargs="?",
        default="run",
        help="Command to execute (default: run)",
    )

    args = parser.parse_args()

    # Enforce SQLAlchemy runtime SQLite compatibility
    os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT_RUNTIME", "1")
    os.environ.setdefault("PYTHONPATH", str(ROOT_DIR))

    if args.command == "run":
        run_app()
    elif args.command == "init-db":
        init_db()
    elif args.command == "seed-db":
        seed_db()
    elif args.command == "train-model":
        train_model()
    elif args.command == "test":
        run_tests()


if __name__ == "__main__":
    main()
