from pathlib import Path

import pandas as pd

from pharmacy_stock.analysis import (
    calculate_inventory_accuracy,
    calculate_total_inventory_value,
    summarize_discrepancies,
    get_top_stock_value_products,
)

from pharmacy_stock.visualization import (
    plot_inventory_value,
    plot_inventory_accuracy,
    plot_discrepancy_distribution,
    plot_top_stock_value_products,
)


INPUT_FILE = Path(
    "data/processed/inventory_2026_08.parquet"
)

OUTPUT_DIR = Path(
    "reports/figures"
)


def main():
    print("Starting inventory visualization...")

    # --------------------------------------------------
    # Load processed inventory
    # --------------------------------------------------

    df = pd.read_parquet(INPUT_FILE)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------
    # Calculate KPIs
    # --------------------------------------------------

    total_value = calculate_total_inventory_value(df)

    accuracy = calculate_inventory_accuracy(df)

    discrepancy_summary = summarize_discrepancies(df)

    # --------------------------------------------------
    # Visualization 1
    # --------------------------------------------------

    fig = plot_inventory_value(total_value)

    fig.savefig(
        OUTPUT_DIR / "inventory_value.png",
        dpi=150,
        bbox_inches="tight",
    )

    # --------------------------------------------------
    # Visualization 2
    # --------------------------------------------------

    fig = plot_inventory_accuracy(accuracy)

    fig.savefig(
        OUTPUT_DIR / "inventory_accuracy.png",
        dpi=150,
        bbox_inches="tight",
    )

    # --------------------------------------------------
    # Visualization 3
    # --------------------------------------------------

    fig = plot_discrepancy_distribution(
        discrepancy_summary
    )

    fig.savefig(
        OUTPUT_DIR / "discrepancy_distribution.png",
        dpi=150,
        bbox_inches="tight",
    )

    # --------------------------------------------------
    # Visualization 4
    # --------------------------------------------------

    fig = plot_top_stock_value_products(
        df,
        n=10,
    )

    fig.savefig(
        OUTPUT_DIR / "top_stock_value_products.png",
        dpi=150,
        bbox_inches="tight",
    )

    print("\nVisualizations generated:")
    print(
        f"  {OUTPUT_DIR / 'inventory_value.png'}"
    )
    print(
        f"  {OUTPUT_DIR / 'inventory_accuracy.png'}"
    )
    print(
        f"  {OUTPUT_DIR / 'discrepancy_distribution.png'}"
    )
    print(
        f"  {OUTPUT_DIR / 'top_stock_value_products.png'}"
    )


if __name__ == "__main__":
    main()
