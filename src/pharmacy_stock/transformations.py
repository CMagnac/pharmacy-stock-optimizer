import pandas as pd

COLUMN_MAPPING = {
    "Code produit": "product_code",

    # Normal UTF-8 version
    "Désignation": "designation",

    # Replacement-character version found in the pharmacy export
    "D�signation": "designation",

    "Date": "inventory_date",
    "Stock avant": "stock_before",

    "Stock modifié": "stock_after",
    "Stock modifi�": "stock_after",

    "Ecart": "stock_difference",
    "PAMP net": "net_purchase_price",
    "Ecart en PAMP net": "difference_value",
}

PROCESSED_COLUMNS = [
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


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename source columns to standardized internal names.
    """

    df = df.copy()

    return df.rename(columns=COLUMN_MAPPING)


def clean_inventory_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and convert inventory data to appropriate data types.
    """

    df = df.copy()

    df["product_code"] = (
        df["product_code"]
        .astype("string")
        .str.strip()
    )

    df["designation"] = (
        df["designation"]
        .astype("string")
        .str.strip()
    )

    df["inventory_date"] = pd.to_datetime(
        df["inventory_date"],
        dayfirst=True,
        errors="coerce",
    )

    numeric_columns = [
        "stock_before",
        "stock_after",
        "stock_difference",
        "net_purchase_price",
        "difference_value",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["stock_value"] = (
        df["stock_after"]
        * df["net_purchase_price"]
    )

    df["absolute_difference_value"] = (
        df["difference_value"].abs()
    )

    return df


def select_processed_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep only the columns required for analysis.
    """

    return df[PROCESSED_COLUMNS].copy()
