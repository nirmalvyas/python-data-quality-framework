from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CheckResult:
    check_name: str
    column: str
    success: bool
    failed_indexes: set[Any] = field(default_factory=set)
    details: str = ""


@dataclass(frozen=True)
class FileValidationResult:
    file_path: Path
    records_scanned: int
    failed_records: int
    failed_dataframe: pd.DataFrame
    check_results: list[CheckResult]

    @property
    def failure_percentage(self) -> float:
        if self.records_scanned == 0:
            return 0.0
        return (self.failed_records / self.records_scanned) * 100
