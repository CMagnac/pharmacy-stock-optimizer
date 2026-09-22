import matplotlib.pyplot as plt
import pandas as pd


def plot_inventory_value(total_value: float):
    """
    Display total pharmacy inventory value.
    """

    fig, ax = plt.subplots(figsize=(8, 4))

    ax.text(
        0.5,
        0.55,
        f"€{total_value:,.2f}",
        ha="center",
        va="center",
        fontsize=32,
        fontweight="bold",
    )

    ax.text(
        0.5,
        0.25,
        "Total inventory value",
        ha="center",
        va="center",
        fontsize=14,
    )

    ax.axis("off")

    return fig


def plot_inventory_accuracy(accuracy: float):
    """
    Display percentage of products without inventory discrepancy.
    """

    fig, ax = plt.subplots(figsize=(8, 4))

    ax.text(
        0.5,
        0.55,
        f"{accuracy:.2f}%",
        ha="center",
        va="center",
        fontsize=32,
        fontweight="bold",
    )

    ax.text(
        0.5,
        0.25,
        "Products without discrepancy",
        ha="center",
        va="center",
        fontsize=14,
    )

    ax.axis("off")

    return fig


def plot_discrepancy_distribution(summary: dict):
    """
    Plot the distribution of inventory discrepancies.

    Categories:
    - No difference
    - Negative difference
    - Positive difference
    """

    categories = [
        "No difference",
        "Negative",
        "Positive",
    ]

    values = [
        summary["products_with_no_difference"],
        summary["products_with_negative_difference"],
        summary["products_with_positive_difference"],
    ]

    fig, ax = plt.subplots(figsize=(8, 5))

    bars = ax.bar(categories, values)

    ax.set_title("Inventory discrepancy distribution")
    ax.set_ylabel("Number of products")

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(value),
            ha="center",
            va="bottom",
        )

    fig.tight_layout()

    return fig


def plot_top_stock_value_products(
    df: pd.DataFrame,
    n: int = 10,
):
    """
    Plot the top N products by inventory value.
    """

    top_products = (
        df.sort_values(
            "stock_value",
            ascending=False,
        )
        .head(n)
        .sort_values("stock_value")
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.barh(
        top_products["designation"],
        top_products["stock_value"],
    )

    ax.set_title(
        f"Top {n} products by inventory value"
    )

    ax.set_xlabel("Inventory value (€)")

    fig.tight_layout()

    return fig
