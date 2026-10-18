import pandas as pd


MONTHLY_SNAPSHOT_COLUMNS = [
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
]


def create_monthly_snapshot(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a standardized monthly inventory snapshot.
    """

    missing_columns = [
        column
        for column in MONTHLY_SNAPSHOT_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing snapshot columns: {missing_columns}"
        )

    return (
        df[MONTHLY_SNAPSHOT_COLUMNS]
        .copy()
        .sort_values(
            ["inventory_date", "product_code"]
        )
        .reset_index(drop=True)
    )
