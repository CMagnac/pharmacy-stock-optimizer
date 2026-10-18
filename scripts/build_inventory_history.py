from pathlib import Path

import pandas as pd


AUGUST_FILE = Path("data/processed/inventory_2026_08.parquet")
SEPTEMBER_FILE = Path(
    "data/processed/inventory_2026_09_monitored.parquet"
)
OUTPUT_FILE = Path(
    "data/processed/monitored_inventory_history.parquet"
)

SNAPSHOT_COLUMNS = [
    "product_code",
    "designation",
    "inventory_date",
    "stock_before",
    "stock_after",
    "stock_difference",
    "net_purchase_price",
    "difference_value",
    "stock_value",
    "absolute_difference_value",
    "observation_status",
    "snapshot_month",
]


def standardize_snapshot(
    df: pd.DataFrame,
    snapshot_month: str,
) -> pd.DataFrame:
    """Standardize one monthly snapshot."""

    df = df.copy()

    # Every product in the August inventory was observed.
    if "observation_status" not in df.columns:
        df["observation_status"] = "observed"

    # Record the reporting month independently of inventory_date.
    df["snapshot_month"] = snapshot_month

    # Check that all expected columns are available.
    missing_columns = [
        column
        for column in SNAPSHOT_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns for {snapshot_month}: "
            f"{missing_columns}"
        )

    return df[SNAPSHOT_COLUMNS].copy()


def validate_history(df: pd.DataFrame) -> None:
    """Validate the combined historical dataset."""

    if df["product_code"].isna().any():
        raise ValueError("History contains missing product codes.")

    # One row per product per reporting month.
    duplicated = df.duplicated(
        subset=["product_code", "snapshot_month"]
    )

    if duplicated.any():
        raise ValueError(
            "Duplicate product/month combinations found:\n"
            f"{df.loc[duplicated, ['product_code', 'snapshot_month']]}"
        )

    allowed_statuses = {"observed", "missing"}

    unexpected_statuses = (
        set(df["observation_status"].dropna())
        - allowed_statuses
    )

    if unexpected_statuses:
        raise ValueError(
            f"Unexpected observation statuses: {unexpected_statuses}"
        )

    # Missing observations must not be mistaken for zero stock.
    missing = df["observation_status"].eq("missing")

    stock_columns = [
        "stock_before",
        "stock_after",
        "stock_difference",
        "net_purchase_price",
        "difference_value",
        "stock_value",
        "absolute_difference_value",
    ]

    if df.loc[missing, stock_columns].notna().any().any():
        raise ValueError(
            "Missing observations contain stock or value data."
        )

    # Observed rows must have an inventory date.
    observed = df["observation_status"].eq("observed")

    if df.loc[observed, "inventory_date"].isna().any():
        raise ValueError(
            "Observed products have a missing inventory date."
        )


def main() -> None:
    print("Building monitored inventory history...")

    august = pd.read_parquet(AUGUST_FILE)
    september = pd.read_parquet(SEPTEMBER_FILE)

    august = standardize_snapshot(august, "2026-08")
    september = standardize_snapshot(september, "2026-09")

    history = pd.concat(
        [august, september],
        ignore_index=True,
    )

    history = history.sort_values(
        ["snapshot_month", "product_code"],
        na_position="last",
    ).reset_index(drop=True)

    validate_history(history)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    history.to_parquet(OUTPUT_FILE, index=False)

    print("\nHistorical inventory summary")
    print("----------------------------")
    print(f"Total rows: {len(history)}")
    print(f"Unique products: {history['product_code'].nunique()}")
    print("\nRows by month:")
    print(history["snapshot_month"].value_counts().sort_index())

    print("\nObservation status by month:")
    print(
        history.groupby(
            ["snapshot_month", "observation_status"]
        ).size()
    )

    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
