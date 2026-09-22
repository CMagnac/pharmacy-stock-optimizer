import pandas as pd


def calculate_total_inventory_value(
    df: pd.DataFrame,
) -> float:
    """
    Calculate the total value of the pharmacy inventory.

    Inventory value is calculated as:

        stock_after * net_purchase_price

    Returns
    -------
    float
        Total inventory value.
    """
    return float(df["stock_value"].sum())


def summarize_discrepancies(
    df: pd.DataFrame,
) -> dict:
    """
    Summarize inventory discrepancies.

    Products are classified into three categories:

        negative : stock_difference < 0
        zero     : stock_difference == 0
        positive : stock_difference > 0

    Returns
    -------
    dict
        Summary statistics about inventory discrepancies.
    """

    negative = df["stock_difference"] < 0
    zero = df["stock_difference"] == 0
    positive = df["stock_difference"] > 0

    return {
        "total_products": len(df),
        "products_with_no_difference": int(zero.sum()),
        "products_with_negative_difference": int(
            negative.sum()
        ),
        "products_with_positive_difference": int(
            positive.sum()
        ),
        "total_absolute_difference_value": float(
            df["absolute_difference_value"].sum()
        ),
        "total_difference_value": float(
            df["difference_value"].sum()
        ),
    }


def get_top_stock_value_products(
    df: pd.DataFrame,
    n: int = 20,
) -> pd.DataFrame:
    """
    Return the products with the highest inventory value.
    """

    columns = [
        "product_code",
        "designation",
        "stock_after",
        "net_purchase_price",
        "stock_value",
    ]

    return (
        df.sort_values(
            "stock_value",
            ascending=False,
        )[columns]
        .head(n)
        .reset_index(drop=True)
    )


def get_top_negative_discrepancies(
    df: pd.DataFrame,
    n: int = 20,
) -> pd.DataFrame:
    """
    Return products with the largest negative
    inventory discrepancies by financial value.
    """

    columns = [
        "product_code",
        "designation",
        "stock_before",
        "stock_after",
        "stock_difference",
        "net_purchase_price",
        "difference_value",
    ]

    result = df[df["stock_difference"] < 0]

    return (
        result.sort_values(
            "difference_value",
            ascending=True,
        )[columns]
        .head(n)
        .reset_index(drop=True)
    )


def get_top_positive_discrepancies(
    df: pd.DataFrame,
    n: int = 20,
) -> pd.DataFrame:
    """
    Return products with the largest positive
    inventory discrepancies by financial value.
    """

    columns = [
        "product_code",
        "designation",
        "stock_before",
        "stock_after",
        "stock_difference",
        "net_purchase_price",
        "difference_value",
    ]

    result = df[df["stock_difference"] > 0]

    return (
        result.sort_values(
            "difference_value",
            ascending=False,
        )[columns]
        .head(n)
        .reset_index(drop=True)
    )

def calculate_inventory_accuracy(
    df: pd.DataFrame,
) -> float:
    """
    Calculate the percentage of products with no
    inventory discrepancy.
    """

    if len(df) == 0:
        return 0.0

    products_without_difference = (
        df["stock_difference"] == 0
    ).sum()

    return float(
        products_without_difference
        / len(df)
        * 100
    )
