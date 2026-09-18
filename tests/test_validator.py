import pandas as pd

from pharmacy_stock.validator import (
    validate_stock_difference,
    generate_validation_report,
)


def test_validate_stock_difference():

    df = pd.DataFrame(
        {
            "product_code": ["A", "B"],
            "stock_before": [2, 5],
            "stock_after": [3, 4],
            "stock_difference": [1, -1],
        }
    )

    errors = validate_stock_difference(df)

    assert len(errors) == 0


def test_detect_difference_error():

    df = pd.DataFrame(
        {
            "product_code": ["A"],
            "stock_before": [2],
            "stock_after": [5],
            "stock_difference": [1],
        }
    )

    errors = validate_stock_difference(df)

    assert len(errors) == 1


def test_validation_report():

    df = pd.DataFrame(
        {
            "product_code": ["A", "B"],
            "stock_before": [2, 5],
            "stock_after": [3, 4],
            "stock_difference": [1, -1],
            "net_purchase_price": [10.0, 20.0],
        }
    )

    report = generate_validation_report(df)

    assert report["rows"] == 2
    assert report["unique_products"] == 2
    assert report["difference_errors"] == 0
