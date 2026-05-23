from __future__ import annotations

from pathlib import Path

import great_expectations as gx
import pandas as pd
from great_expectations.data_context.types.base import ProgressBarsConfig

from data_quality.checks import DataQualityCheck
from data_quality.io import ErrorWriter, FileReader
from data_quality.logging_utils import log_execution
from data_quality.models import FileValidationResult


class GreatExpectationsPandasValidator:
    """Validation engine backed by Great Expectations' Pandas data source."""

    def __init__(self) -> None:
        # Ephemeral mode keeps the assignment self-contained: no gx/ project
        # directory is generated and every run builds its suite from config.
        self.context = gx.get_context(mode="ephemeral")
        self.context.variables.progress_bars = ProgressBarsConfig(globally=False)

    @log_execution("Build and run Great Expectations suite")
    def run_expectations(
        self,
        dataframe: pd.DataFrame,
        file_name: str,
        checks: list[DataQualityCheck],
    ) -> None:
        data_source_name = f"{file_name}_pandas_source"
        asset_name = f"{file_name}_dataframe_asset"
        batch_name = f"{file_name}_batch"
        suite_name = f"{file_name}_suite"
        validation_name = f"{file_name}_validation"

        # A dataframe asset lets Great Expectations validate in-memory Pandas
        # data while the FileReader remains responsible for input file formats.
        data_source = self.context.data_sources.add_pandas(name=data_source_name)
        data_asset = data_source.add_dataframe_asset(name=asset_name)
        batch_definition = data_asset.add_batch_definition_whole_dataframe(batch_name)

        # Checks own their expectation definitions, so the validator does not
        # need to know the details of each rule type.
        suite = gx.ExpectationSuite(name=suite_name)
        for check in checks:
            check.add_expectation(suite)
        suite = self.context.suites.add(suite)

        validation_definition = gx.ValidationDefinition(
            name=validation_name,
            data=batch_definition,
            suite=suite,
        )
        validation_definition = self.context.validation_definitions.add(validation_definition)
        validation_definition.run(batch_parameters={"dataframe": dataframe})


class FileValidator:
    def __init__(
        self,
        reader: FileReader,
        error_writer: ErrorWriter,
        gx_validator: GreatExpectationsPandasValidator,
    ) -> None:
        self.reader = reader
        self.error_writer = error_writer
        self.gx_validator = gx_validator

    @log_execution("Validate file")
    def validate(self, file_path: Path, checks: list[DataQualityCheck]) -> FileValidationResult:
        dataframe = self.reader.read(file_path)
        self._validate_columns_exist(dataframe, checks)

        # Run GE for the official expectation validation path.
        self.gx_validator.run_expectations(dataframe, file_path.stem, checks)

        # Evaluate row indexes locally so ERR output contains full failed
        # records with readable rule names.
        check_results = [check.evaluate(dataframe) for check in checks]
        failed_indexes = set().union(*(result.failed_indexes for result in check_results))
        failed_dataframe = dataframe.loc[sorted(failed_indexes)].copy()

        if not failed_dataframe.empty:
            # Add a compact reason column before writing the failed records.
            failed_dataframe.insert(
                0,
                "dq_errors",
                failed_dataframe.index.map(
                    lambda row_index: self._errors_for_row(row_index, check_results)
                ),
            )

        self.error_writer.write_failed_records(file_path, failed_dataframe)

        return FileValidationResult(
            file_path=file_path,
            records_scanned=len(dataframe),
            failed_records=len(failed_dataframe),
            failed_dataframe=failed_dataframe,
            check_results=check_results,
        )

    @staticmethod
    def _validate_columns_exist(
        dataframe: pd.DataFrame,
        checks: list[DataQualityCheck],
    ) -> None:
        # Fail fast when config references a missing column; otherwise the
        # validation error would be less obvious later in the pipeline.
        missing_columns = sorted(
            {
                column
                for check in checks
                for column in check.required_columns
                if column not in dataframe.columns
            }
        )
        if missing_columns:
            raise ValueError(f"Input file is missing configured columns: {missing_columns}")

    @staticmethod
    def _errors_for_row(row_index: int, check_results: list) -> str:
        errors = [
            f"{result.check_name}({result.column})"
            for result in check_results
            if row_index in result.failed_indexes
        ]
        return "; ".join(errors)
