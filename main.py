from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")

from data_quality.runner import run_from_cli


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the data quality framework.")
    parser.add_argument(
        "--config",
        default="config/dq_config.json",
        help="Path to the JSON validation config.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_from_cli(args.config)
