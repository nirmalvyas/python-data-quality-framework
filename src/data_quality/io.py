from __future__ import annotations

from pathlib import Path

import pandas as pd


class FileReader:
    def read(self, file_path: Path) -> pd.DataFrame:
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(file_path, dtype=str, keep_default_na=True)
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(file_path, dtype=str)
        raise ValueError(f"Unsupported input file type: {file_path.suffix}")


class ErrorWriter:
    def __init__(self, err_folder: Path) -> None:
        self.err_folder = err_folder
        self.err_folder.mkdir(parents=True, exist_ok=True)

    def write_failed_records(self, source_file: Path, failed_dataframe: pd.DataFrame) -> Path | None:
        if failed_dataframe.empty:
            return None

        output_path = self.err_folder / f"{source_file.stem}_failed_records.csv"
        failed_dataframe.to_csv(output_path, index=False)
        return output_path
