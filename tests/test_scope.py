import pandas as pd

from pharmacy_stock.scope import (
    compare_product_scope,
    calculate_financial_coverage,
)


def test_compare_product_scope():
    full_inventory = pd.DataFrame(
        {
            "product_code": [
                "A",
                "B",
                "C",
                "D",
                "E",
            ],
            "stock_value": [
                100.0,
                200.0,
                300.0,
                400.0,
                500.0,
            ],
        }
    )

    monitored_inventory = pd.DataFrame(
        {
            "product_code": [
                "A",
                "B",
                "X",
            ]
        }
    )

    result = compare_product_scope(
        full_inventory,
        monitored_inventory,
    )

    assert result["total_full_products"] == 5
    assert result["total_monitored_products"] == 3
    assert result["monitored_products_found"] == 2
    assert result["monitored_products_missing"] == 1
    assert result["products_not_monitored"] == 3

    assert result["product_coverage_percent"] == 40.0


def test_calculate_financial_coverage():
    full_inventory = pd.DataFrame(
        {
            "product_code": [
                "A",
                "B",
                "C",
            ],
            "stock_value": [
                100.0,
                200.0,
                700.0,
            ],
        }
    )

    result = calculate_financial_coverage(
        full_inventory,
        {"A", "B"},
    )

    assert result["full_inventory_value"] == 1000.0
    assert result["monitored_inventory_value"] == 300.0
    assert result["financial_coverage_percent"] == 30.0
