from pathlib import Path

import pandas as pd

from .data_loader import load_inventory_csv
from .transformations import (
    clean_inventory_data,
    select_processed_columns,
    standardize_columns,
)
from .validator import (
    generate_validation_report,
    validate_required_columns,
)


def process_inventory(
    file_path: str | Path,
) -> tuple[pd.DataFrame, dict]:
    """
    Complete inventory ingestion and cleaning pipeline.
    """

    # 1. Load raw CSV
    df = load_inventory_csv(file_path)

    # 2. Standardize column names
    df = standardize_columns(df)

    # 3. Check required columns
    missing_columns = validate_required_columns(df)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # 4. Clean data
    df = clean_inventory_data(df)

    # 5. Validate data
    report = generate_validation_report(df)

    # 6. Keep analytical columns only
    df = select_processed_columns(df)

    return df, report
