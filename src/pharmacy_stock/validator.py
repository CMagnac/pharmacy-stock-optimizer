import pandas as pd


REQUIRED_COLUMNS = [
    "product_code",
    "designation",
    "inventory_date",
    "stock_before",
    "stock_after",
    "stock_difference",
    "net_purchase_price",
]


def validate_required_columns(df: pd.DataFrame) -> list[str]:
    """
    Return required columns that are missing.
    """

    return [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]


def find_missing_values(df: pd.DataFrame) -> pd.Series:
    """
    Count missing values for each column.
    """

    return df.isna().sum()


def find_duplicate_products(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Find duplicated product codes.
    """

    duplicates = df[
        df["product_code"].duplicated(keep=False)
    ]

    return duplicates.sort_values("product_code")


def validate_stock_difference(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Check whether:

        stock_difference =
        stock_after - stock_before
    """

    calculated_difference = (
        df["stock_after"] - df["stock_before"]
    )

    errors = df[
        ~calculated_difference.round(2).eq(
            df["stock_difference"].round(2)
        )
    ].copy()

    return errors


def validate_non_negative_stock(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Find products with negative stock values.
    """

    return df[
        (df["stock_before"] < 0)
        | (df["stock_after"] < 0)
    ].copy()

def generate_validation_report(
    df: pd.DataFrame,
) -> dict:
    """
    Generate a global validation report.
    """

    difference_errors = validate_stock_difference(df)
    negative_stock = validate_non_negative_stock(df)

    duplicate_products = df[
        df["product_code"].duplicated(keep=False)
    ]

    missing_values = df.isna().sum()

    available_required_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column in df.columns
    ]

    required_missing_values = (
        df[available_required_columns]
        .isna()
        .sum()
    )

    report = {
        "rows": len(df),
        "unique_products": df["product_code"].nunique(),
        "duplicate_rows": int(
            df.duplicated().sum()
        ),
        "duplicate_products": int(
            duplicate_products["product_code"].nunique()
        ),
        "difference_errors": len(
            difference_errors
        ),
        "negative_stock_rows": len(
            negative_stock
        ),
        "required_missing_values": (
            required_missing_values[
                required_missing_values > 0
            ].to_dict()
        ),
        "optional_missing_values": (
            missing_values[
                ~missing_values.index.isin(
                    REQUIRED_COLUMNS
                )
                & (missing_values > 0)
            ].to_dict()
        ),
    }

    return report
