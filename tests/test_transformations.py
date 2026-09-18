import pandas as pd

from pharmacy_stock.transformations import (
    standardize_columns,
    clean_inventory_data,
)


def test_standardize_columns():

    df = pd.DataFrame(
        {
            "Code produit": ["123"],
            "Désignation": ["TEST DRUG"],
            "Stock avant": [2],
            "Stock modifié": [3],
        }
    )

    result = standardize_columns(df)

    assert "product_code" in result.columns
    assert "designation" in result.columns
    assert "stock_before" in result.columns
    assert "stock_after" in result.columns


def test_clean_inventory_data():

    df = pd.DataFrame(
        {
            "product_code": ["123"],
            "designation": ["TEST DRUG"],
            "inventory_date": ["19/08/2026 15:04"],
            "stock_before": ["2"],
            "stock_after": ["3"],
            "stock_difference": ["1"],
            "net_purchase_price": ["10.50"],
            "difference_value": ["10.50"],
        }
    )

    result = clean_inventory_data(df)

    assert pd.api.types.is_datetime64_any_dtype(
        result["inventory_date"]
    )

    assert result["stock_after"].iloc[0] == 3
    assert result["stock_value"].iloc[0] == 31.50
