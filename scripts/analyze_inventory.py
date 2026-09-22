from pathlib import Path

import pandas as pd

from pharmacy_stock.analysis import (
    calculate_inventory_accuracy,
    calculate_total_inventory_value,
    get_top_negative_discrepancies,
    get_top_positive_discrepancies,
    get_top_stock_value_products,
    summarize_discrepancies,
)

INPUT_FILE = Path(
    "data/processed/inventory_2026_08.parquet"
)


def main():
    print("Starting inventory analysis...")

    df = pd.read_parquet(INPUT_FILE)

    # --------------------------------------------------
    # Inventory valuation
    # --------------------------------------------------

    total_value = calculate_total_inventory_value(df)

    print("\nInventory valuation")
    print("===================")
    print(
        f"Total inventory value: €{total_value:,.2f}"
    )

    # --------------------------------------------------
    # Discrepancy summary
    # --------------------------------------------------

    discrepancy_summary = summarize_discrepancies(df)

    print("\nInventory discrepancies")
    print("=======================")

    for key, value in discrepancy_summary.items():
        print(f"{key}: {value}")

    # --------------------------------------------------
    # Top stock value products
    # --------------------------------------------------

    print("\nTop 10 products by inventory value")
    print("===================================")

    top_stock = get_top_stock_value_products(
        df,
        n=10,
    )

    print(top_stock.to_string(index=False))

    # --------------------------------------------------
    # Negative discrepancies
    # --------------------------------------------------

    print("\nTop negative discrepancies")
    print("==========================")

    negative = get_top_negative_discrepancies(
        df,
        n=10,
    )

    if negative.empty:
        print("No negative discrepancies.")
    else:
        print(negative.to_string(index=False))

    # --------------------------------------------------
    # Positive discrepancies
    # --------------------------------------------------

    print("\nTop positive discrepancies")
    print("==========================")

    positive = get_top_positive_discrepancies(
        df,
        n=10,
    )

    if positive.empty:
        print("No positive discrepancies.")
    else:
        print(positive.to_string(index=False))

    # --------------------------------------------------
    # Inventory accuracy
    # --------------------------------------------------

    accuracy = calculate_inventory_accuracy(df)

    print("\nInventory accuracy")
    print("==================")
    print(f"Products without discrepancy: {accuracy:.2f}%")

if __name__ == "__main__":
    main()
