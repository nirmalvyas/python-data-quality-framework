# Python Data Quality Framework

Python-based data quality framework using Great Expectations `v1.3.x` with the Pandas engine.

## What It Does

- Reads input files from `RAW/`
- Includes two sample sources:
  - a small local `customers.csv`
  - Kaggle renewable energy share data from <https://www.kaggle.com/datasets/elvisbui/renewable-energy-share-by-country-2000-2025>
- Applies config-driven checks:
  - not null
  - unique column values
  - unique column combinations
  - datatype validation
- Writes failed records to `ERR/<input>_failed_records.csv`
- Prints an execution summary with records scanned, failed records, and failure percentage

## Design Choices

The framework is object-oriented and intentionally small:

- `DataQualityCheck` is the base class for pluggable checks.
- `NotNullCheck`, `UniqueCheck`, `UniqueCombinationCheck`, and `DatatypeCheck` implement validation rules.
- `CheckFactory` builds checks from `config/dq_config.json`, so new files/checks can be added without changing runner code.
- `GreatExpectationsPandasValidator` creates an ephemeral Great Expectations context and validates a Pandas dataframe batch.
- `FileReader`, `ErrorWriter`, `FileValidator`, and `DataQualityRunner` keep IO, validation, and orchestration separate.
- `@log_execution` provides consistent start/end, elapsed time, and success/failure logging for key framework steps.

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Run

```powershell
.\.venv\Scripts\python main.py --config config/dq_config.json
```

## Sample Run Output

```text
Data Quality Execution Summary
================================
File: customers.csv
Records scanned: 7
Failed records: 6
Failure %: 85.71%
Check details:
  - PASS | not_null | customer_id | 0 failed row(s)
  - FAIL | not_null | name | 1 failed row(s)
  - FAIL | not_null | email | 1 failed row(s)
  - PASS | not_null | signup_date | 0 failed row(s)
  - FAIL | unique | customer_id | 2 failed row(s)
  - FAIL | unique | email | 2 failed row(s)
  - PASS | datatype | customer_id | expected=int64; 0 failed row(s)
  - PASS | datatype | name | expected=object; 0 failed row(s)
  - PASS | datatype | email | expected=object; 0 failed row(s)
  - FAIL | datatype | age | expected=int64; 1 failed row(s)
  - FAIL | datatype | signup_date | expected=datetime64[ns]; 1 failed row(s)
--------------------------------
File: renewable_energy_share_2000_2025.csv
Records scanned: 7636
Failed records: 4
Failure %: 0.05%
Check details:
  - FAIL | not_null | country | 1 failed row(s)
  - PASS | not_null | year | 0 failed row(s)
  - FAIL | unique_combination | country+year | 2 failed row(s)
  - PASS | datatype | country | expected=object; 0 failed row(s)
  - FAIL | datatype | year | expected=int64; 1 failed row(s)
  - PASS | datatype | population | expected=float64; 0 failed row(s)
  - FAIL | datatype | electricity_generation | expected=float64; 1 failed row(s)
  - PASS | datatype | electricity_demand | expected=float64; 0 failed row(s)
  - PASS | datatype | renewables_share_energy | expected=float64; 0 failed row(s)
  - FAIL | datatype | renewables_share_elec | expected=float64; 1 failed row(s)
  - PASS | datatype | fossil_share_energy | expected=float64; 0 failed row(s)
  - PASS | datatype | fossil_share_elec | expected=float64; 0 failed row(s)
  - PASS | datatype | solar_electricity | expected=float64; 0 failed row(s)
  - PASS | datatype | wind_electricity | expected=float64; 0 failed row(s)
  - PASS | datatype | hydro_electricity | expected=float64; 0 failed row(s)
--------------------------------
```
