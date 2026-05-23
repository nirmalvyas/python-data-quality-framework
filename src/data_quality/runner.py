from __future__ import annotations

import json
from pathlib import Path

from data_quality.checks import CheckFactory
from data_quality.io import ErrorWriter, FileReader
from data_quality.logging_utils import configure_logging, log_execution
from data_quality.models import FileValidationResult
from data_quality.validator import FileValidator, GreatExpectationsPandasValidator


class DataQualityRunner:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.project_root = config_path.parent.parent

    @log_execution("Run data quality framework")
    def run(self) -> list[FileValidationResult]:
        config = self._load_config()
        raw_folder = self.project_root / config.get("raw_folder", "RAW")
        err_folder = self.project_root / config.get("err_folder", "ERR")

        # Reuse the same components for every configured file so adding a new
        # dataset is a config change, not an orchestration-code change.
        file_validator = FileValidator(
            reader=FileReader(),
            error_writer=ErrorWriter(err_folder),
            gx_validator=GreatExpectationsPandasValidator(),
        )

        results: list[FileValidationResult] = []
        for file_config in config["files"]:
            file_path = raw_folder / file_config["file_name"]
            checks = []
            for check_config in file_config["checks"]:
                # One config entry can expand into several concrete checks,
                # for example datatype checks across multiple columns.
                checks.extend(CheckFactory.from_config(check_config))

            results.append(file_validator.validate(file_path, checks))

        self._print_summary(results)
        return results

    def _load_config(self) -> dict:
        with self.config_path.open("r", encoding="utf-8") as config_file:
            return json.load(config_file)

    @staticmethod
    def _print_summary(results: list[FileValidationResult]) -> None:
        print("\nData Quality Execution Summary")
        print("=" * 32)
        for result in results:
            print(f"File: {result.file_path.name}")
            print(f"Records scanned: {result.records_scanned}")
            print(f"Failed records: {result.failed_records}")
            print(f"Failure %: {result.failure_percentage:.2f}%")
            print("Check details:")
            for check_result in result.check_results:
                status = "PASS" if check_result.success else "FAIL"
                print(
                    f"  - {status} | {check_result.check_name} | "
                    f"{check_result.column} | {check_result.details}"
                )
            print("-" * 32)


def run_from_cli(config_path: str) -> None:
    configure_logging()
    DataQualityRunner(Path(config_path)).run()
