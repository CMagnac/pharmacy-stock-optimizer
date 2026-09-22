import pandas as pd

import pytest

from pharmacy_stock.analysis import (
    calculate_total_inventory_value,
    get_top_negative_discrepancies,
    get_top_positive_discrepancies,
    get_top_stock_value_products,
    summarize_discrepancies,
)


@pytest.fixture
def inventory_data():
    return pd.DataFrame(
        {
            "product_code": [
                "A",
                "B",
                "C",
                "D",
            ],
            "designation": [
                "DRUG A",
                "DRUG B",
                "DRUG C",
                "DRUG D",
            ],
            "stock_before": [
                10,
                5,
                20,
                8,
            ],
            "stock_after": [
                10,
                3,
                25,
                6,
            ],
            "stock_difference": [
                0,
                -2,
                5,
                -2,
            ],
            "net_purchase_price": [
                10.0,
                20.0,
                5.0,
                50.0,
            ],
            "stock_value": [
                100.0,
                60.0,
                125.0,
                300.0,
            ],
            "difference_value": [
                0.0,
                -40.0,
                25.0,
                -100.0,
            ],
            "absolute_difference_value": [
                0.0,
                40.0,
                25.0,
                100.0,
            ],
        }
    )


def test_calculate_total_inventory_value(
    inventory_data,
):
    result = calculate_total_inventory_value(
        inventory_data
    )

    assert result == 585.0


def test_summarize_discrepancies(
    inventory_data,
):
    result = summarize_discrepancies(
        inventory_data
    )

    assert result["total_products"] == 4
    assert result["products_with_no_difference"] == 1
    assert result["products_with_negative_difference"] == 2
    assert result["products_with_positive_difference"] == 1
    assert result["total_absolute_difference_value"] == 165.0
    assert result["total_difference_value"] == -115.0


def test_get_top_stock_value_products(
    inventory_data,
):
    result = get_top_stock_value_products(
        inventory_data,
        n=2,
    )

    assert len(result) == 2
    assert result.iloc[0]["product_code"] == "D"
    assert result.iloc[1]["product_code"] == "C"


def test_get_top_negative_discrepancies(
    inventory_data,
):
    result = get_top_negative_discrepancies(
        inventory_data,
        n=2,
    )

    assert len(result) == 2
    assert result.iloc[0]["product_code"] == "D"
    assert result.iloc[1]["product_code"] == "B"


def test_get_top_positive_discrepancies(
    inventory_data,
):
    result = get_top_positive_discrepancies(
        inventory_data,
        n=1,
    )

    assert len(result) == 1
    assert result.iloc[0]["product_code"] == "C"
