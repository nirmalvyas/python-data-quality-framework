from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import great_expectations as gx
import pandas as pd

from data_quality.models import CheckResult


class DataQualityCheck(ABC):
    """Base class for pluggable data quality checks.

    Each check has two jobs:
    1. Add the equivalent Great Expectations expectation to the suite.
    2. Return failing row indexes so this framework can write exact ERR records.
    """

    check_type: str

    def __init__(self, column: str) -> None:
        self.column = column

    @property
    def expectation_name(self) -> str:
        return f"{self.check_type}:{self.column}"

    @property
    def required_columns(self) -> list[str]:
        # Most checks work on one column; multi-column checks override this.
        return [self.column]

    @abstractmethod
    def add_expectation(self, suite: gx.ExpectationSuite) -> None:
        """Add this check's Great Expectations expectation to a suite."""

    @abstractmethod
    def failed_indexes(self, dataframe: pd.DataFrame) -> set[Any]:
        """Return dataframe indexes that fail this check."""

    def evaluate(self, dataframe: pd.DataFrame) -> CheckResult:
        failed = self.failed_indexes(dataframe)
        return CheckResult(
            check_name=self.check_type,
            column=self.column,
            success=len(failed) == 0,
            failed_indexes=failed,
            details=f"{len(failed)} failed row(s)",
        )


class NotNullCheck(DataQualityCheck):
    check_type = "not_null"

    def add_expectation(self, suite: gx.ExpectationSuite) -> None:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column=self.column)
        )

    def failed_indexes(self, dataframe: pd.DataFrame) -> set[Any]:
        return set(dataframe.index[dataframe[self.column].isna()].tolist())


class UniqueCheck(DataQualityCheck):
    check_type = "unique"

    def add_expectation(self, suite: gx.ExpectationSuite) -> None:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeUnique(column=self.column)
        )

    def failed_indexes(self, dataframe: pd.DataFrame) -> set[Any]:
        duplicated = dataframe[self.column].duplicated(keep=False)
        return set(dataframe.index[duplicated].tolist())


class UniqueCombinationCheck(DataQualityCheck):
    check_type = "unique_combination"

    def __init__(self, columns: list[str]) -> None:
        # Store the composite key as a readable label for logs and ERR output.
        self.columns = columns
        super().__init__("+".join(columns))

    @property
    def required_columns(self) -> list[str]:
        return self.columns

    def add_expectation(self, suite: gx.ExpectationSuite) -> None:
        suite.add_expectation(
            gx.expectations.ExpectCompoundColumnsToBeUnique(column_list=self.columns)
        )

    def failed_indexes(self, dataframe: pd.DataFrame) -> set[Any]:
        duplicated = dataframe.duplicated(subset=self.columns, keep=False)
        return set(dataframe.index[duplicated].tolist())


class DatatypeCheck(DataQualityCheck):
    check_type = "datatype"

    def __init__(self, column: str, expected_type: str) -> None:
        super().__init__(column)
        self.expected_type = expected_type

    @property
    def expectation_name(self) -> str:
        return f"{self.check_type}:{self.column}:{self.expected_type}"

    def add_expectation(self, suite: gx.ExpectationSuite) -> None:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeOfType(
                column=self.column,
                type_=self.expected_type,
            )
        )

    def failed_indexes(self, dataframe: pd.DataFrame) -> set[Any]:
        # The CSV reader loads values as strings so invalid source values are not
        # silently converted before validation. We coerce here only to identify
        # rows that cannot be represented as the configured type.
        if self.expected_type == "datetime64[ns]":
            converted = pd.to_datetime(dataframe[self.column], errors="coerce")
            invalid = dataframe[self.column].notna() & converted.isna()
            return set(dataframe.index[invalid].tolist())

        if self.expected_type.startswith("int"):
            converted = pd.to_numeric(dataframe[self.column], errors="coerce")
            invalid = dataframe[self.column].notna() & (
                converted.isna() | (converted % 1 != 0)
            )
            return set(dataframe.index[invalid].tolist())

        if self.expected_type.startswith("float"):
            converted = pd.to_numeric(dataframe[self.column], errors="coerce")
            invalid = dataframe[self.column].notna() & converted.isna()
            return set(dataframe.index[invalid].tolist())

        if self.expected_type in {"object", "str", "string"}:
            non_null = dataframe[self.column].dropna()
            invalid = non_null.map(lambda value: not isinstance(value, str))
            return set(non_null.index[invalid].tolist())

        actual_type = str(dataframe[self.column].dtype)
        if actual_type != self.expected_type:
            return set(dataframe.index.tolist())
        return set()

    def evaluate(self, dataframe: pd.DataFrame) -> CheckResult:
        failed = self.failed_indexes(dataframe)
        return CheckResult(
            check_name=self.check_type,
            column=self.column,
            success=len(failed) == 0,
            failed_indexes=failed,
            details=f"expected={self.expected_type}; {len(failed)} failed row(s)",
        )


class CheckFactory:
    """Build check objects from configuration."""

    @staticmethod
    def from_config(config: dict[str, Any]) -> list[DataQualityCheck]:
        # Adding a new check type only requires a new DataQualityCheck subclass
        # and one branch here to map config into that class.
        check_type = config["type"]
        checks: list[DataQualityCheck] = []

        if check_type == "not_null":
            checks.extend(NotNullCheck(column) for column in config["columns"])
        elif check_type == "unique":
            checks.extend(UniqueCheck(column) for column in config["columns"])
        elif check_type == "unique_combination":
            checks.append(UniqueCombinationCheck(config["columns"]))
        elif check_type == "datatype":
            checks.extend(
                DatatypeCheck(column, expected_type)
                for column, expected_type in config["columns"].items()
            )
        else:
            raise ValueError(f"Unsupported check type: {check_type}")

        return checks
