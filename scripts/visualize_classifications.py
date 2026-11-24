"""
Visualize ABC, XYZ, FSN and ATC5 classification results.

Inputs (relative to the project root):
    data/processed/ABC_product.csv
    data/processed/XYZ_product.csv
    data/processed/FSN_product.csv
    data/processed/demand_classifications_with_atc.parquet

Outputs:
    reports/figures/classification_distributions.png
    reports/figures/abc_xyz_heatmap.png
    reports/figures/combined_classifications.png
    reports/figures/atc5_coverage.png
    reports/figures/top_atc5_codes.png

Run from the project root:
    python scripts\\visualize_classifications.py

Optional:
    python scripts\\visualize_classifications.py --output-dir reports\\figures
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator


# ---------------------------------------------------------------------
# VISUAL IDENTITY
# ---------------------------------------------------------------------

NAVY = "#003366"          # Oxford blue
BLUE = "#3B6EA8"
LIGHT_BLUE = "#A9C5E5"
PALE_BLUE = "#E8F0F8"
GREEN = "#4C956C"
AMBER = "#E0A458"
RED = "#C65D5D"
GREY = "#7A8793"
LIGHT_GREY = "#E9EDF2"
DARK = "#263238"
WHITE = "#FFFFFF"

ABC_COLORS = {"A": NAVY, "B": BLUE, "C": LIGHT_BLUE}
XYZ_COLORS = {"X": GREEN, "Y": AMBER, "Z": RED, "No demand": GREY}
FSN_COLORS = {"F": GREEN, "S": AMBER, "N": GREY}

CLASS_ORDER = {
    "ABC": ["A", "B", "C"],
    "XYZ": ["X", "Y", "Z", "No demand"],
    "FSN": ["F", "S", "N"],
}


# ---------------------------------------------------------------------
# CONFIGURATION AND INPUT VALIDATION
# ---------------------------------------------------------------------

LOGGER = logging.getLogger("visualize_classifications")


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Generate publication-quality classification charts."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=project_root / "data" / "processed",
        help="Directory containing the classification CSV and Parquet files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "reports" / "figures",
        help="Directory where PNG figures will be saved.",
    )
    return parser.parse_args()


def normalize_product_code(series: pd.Series) -> pd.Series:
    """Normalize product identifiers without converting them to integers."""
    result = series.astype("string").str.strip()
    # Remove a trailing decimal suffix if a numeric identifier was read as float.
    result = result.str.replace(r"\.0$", "", regex=True)
    return result


def read_classification_csv(path: Path, classification_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")

    df = pd.read_csv(
        path,
        sep=",",
        dtype={"product_code": "string"},
        encoding="utf-8-sig",
    )

    required = {"product_code", "designation", "class"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(
            f"{path.name} is missing required columns: {sorted(missing)}. "
            f"Found columns: {list(df.columns)}"
        )

    df = df[["product_code", "designation", "class"]].copy()
    df["product_code"] = normalize_product_code(df["product_code"])
    df["designation"] = df["designation"].astype("string").str.strip()
    df["class"] = df["class"].astype("string").str.strip()

    if df["product_code"].isna().any() or df["product_code"].eq("").any():
        raise ValueError(f"{path.name} contains missing product_code values.")

    duplicates = df.loc[df["product_code"].duplicated(keep=False), "product_code"]
    if not duplicates.empty:
        examples = duplicates.drop_duplicates().head(10).tolist()
        raise ValueError(
            f"{path.name} contains duplicate product_code values. "
            f"Examples: {examples}"
        )

    df = df.rename(columns={"class": classification_name})
    LOGGER.info(
        "%s loaded: %s products",
        path.name,
        len(df),
    )
    return df


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find a column using case-insensitive candidate names."""
    lookup = {str(column).lower(): column for column in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def read_atc_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")

    df = pd.read_parquet(path)

    product_col = find_column(df, ["product_code", "cip13", "cip"])
    atc_col = find_column(df, ["atc_code", "ATC_code", "atc5"])

    if product_col is None or atc_col is None:
        raise ValueError(
            f"{path.name} must contain a product identifier and ATC code. "
            f"Found columns: {list(df.columns)}"
        )

    result = df[[product_col, atc_col]].copy()
    result.columns = ["product_code", "ATC_code"]
    result["product_code"] = normalize_product_code(result["product_code"])
    result["ATC_code"] = result["ATC_code"].astype("string").str.strip().str.upper()

    result = result.dropna(subset=["product_code"])
    result = result[result["ATC_code"].notna() & result["ATC_code"].ne("")]

    # This analysis expects ATC level 5 codes (seven characters).
    valid_atc5 = result["ATC_code"].str.fullmatch(r"[A-Z]\d{2}[A-Z]{2}\d{2}")
    invalid_count = int((~valid_atc5).sum())
    if invalid_count:
        LOGGER.warning(
            "%s contains %s non-ATC5 or invalid ATC codes; excluding them.",
            path.name,
            invalid_count,
        )
        result = result.loc[valid_atc5].copy()

    conflicts = (
        result.groupby("product_code")["ATC_code"]
        .nunique()
        .loc[lambda values: values > 1]
    )
    if not conflicts.empty:
        raise ValueError(
            "The enriched Parquet contains multiple ATC5 codes for some "
            f"products. Example product codes: {conflicts.index[:10].tolist()}"
        )

    result = result.drop_duplicates(subset=["product_code"])
    LOGGER.info("ATC5 reference loaded: %s mapped products", len(result))
    return result


def load_data(data_dir: Path) -> pd.DataFrame:
    abc = read_classification_csv(data_dir / "ABC_product.csv", "ABC")
    xyz = read_classification_csv(data_dir / "XYZ_product.csv", "XYZ")
    fsn = read_classification_csv(data_dir / "FSN_product.csv", "FSN")

    # Use ABC as the base registry and require a one-to-one match from
    # the other two classification exports.
    products = abc.merge(
        xyz[["product_code", "XYZ"]],
        on="product_code",
        how="outer",
        validate="one_to_one",
        indicator="_xyz_merge",
    )
    if not products["_xyz_merge"].eq("both").all():
        raise ValueError("ABC and XYZ exports do not contain the same product set.")
    products = products.drop(columns="_xyz_merge")

    products = products.merge(
        fsn[["product_code", "FSN"]],
        on="product_code",
        how="outer",
        validate="one_to_one",
        indicator="_fsn_merge",
    )
    if not products["_fsn_merge"].eq("both").all():
        raise ValueError("ABC and FSN exports do not contain the same product set.")
    products = products.drop(columns="_fsn_merge")

    atc = read_atc_parquet(data_dir / "demand_classifications_with_atc.parquet")
    products = products.merge(
        atc,
        on="product_code",
        how="left",
        validate="one_to_one",
    )

    if products[["ABC", "XYZ", "FSN"]].isna().any().any():
        raise ValueError("One or more products have missing ABC, XYZ or FSN classes.")

    if products["product_code"].duplicated().any():
        raise ValueError("Duplicate product codes found after merging classifications.")

    LOGGER.info("Final monitored product dataset: %s rows", len(products))
    LOGGER.info("ATC5 matched products: %s", products["ATC_code"].notna().sum())
    LOGGER.info("ATC5 unmatched products: %s", products["ATC_code"].isna().sum())

    return products


# ---------------------------------------------------------------------
# PLOTTING HELPERS
# ---------------------------------------------------------------------

def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.labelcolor": DARK,
            "xtick.color": DARK,
            "ytick.color": DARK,
            "text.color": DARK,
            "axes.edgecolor": LIGHT_GREY,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.facecolor": WHITE,
            "figure.facecolor": WHITE,
            "savefig.facecolor": WHITE,
            "savefig.bbox": "tight",
        }
    )


def save_figure(fig: plt.Figure, output_path: Path) -> None:
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    LOGGER.info("Saved: %s", output_path)


def add_bar_labels(ax: plt.Axes, bars, values: list[int]) -> None:
    max_value = max(values) if values else 0
    ax.set_ylim(0, max_value * 1.18 if max_value else 1)
    for bar, value in zip(bars, values):
        ax.annotate(
            f"{value:,}".replace(",", " "),
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )


# ---------------------------------------------------------------------
# FIGURE 1: ABC / XYZ / FSN DISTRIBUTIONS
# ---------------------------------------------------------------------

def plot_classification_distributions(
    df: pd.DataFrame,
    output_dir: Path,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    fig.suptitle(
        "Distribution of monitored products",
        fontsize=17,
        fontweight="bold",
        color=NAVY,
        y=1.04,
    )

    definitions = [
        ("ABC", CLASS_ORDER["ABC"], ABC_COLORS, "Contribution to dispensing events"),
        ("XYZ", CLASS_ORDER["XYZ"], XYZ_COLORS, "Demand variability"),
        ("FSN", CLASS_ORDER["FSN"], FSN_COLORS, "Dispensing frequency"),
    ]

    total = len(df)
    for ax, (column, order, palette, subtitle) in zip(axes, definitions):
        counts = df[column].value_counts().reindex(order, fill_value=0)
        colors = [palette[label] for label in order]
        bars = ax.bar(order, counts.values, color=colors, width=0.65)

        ax.set_title(column, color=NAVY, pad=12)
        ax.set_xlabel(subtitle, labelpad=10)
        ax.set_ylabel("Number of products")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(axis="y", color=LIGHT_GREY, linewidth=0.8)
        ax.set_axisbelow(True)
        add_bar_labels(ax, bars, counts.astype(int).tolist())

        for tick in ax.get_xticklabels():
            tick.set_fontweight("bold")

    fig.text(
        0.5,
        -0.03,
        f"Monitored products: {total} | Demand measured as dispensing events, not boxes",
        ha="center",
        fontsize=9,
        color=GREY,
    )
    fig.tight_layout()
    save_figure(fig, output_dir / "classification_distributions.png")


# ---------------------------------------------------------------------
# FIGURE 2: ABC × XYZ HEATMAP
# ---------------------------------------------------------------------

def plot_abc_xyz_heatmap(df: pd.DataFrame, output_dir: Path) -> None:
    abc_order = ["A", "B", "C"]
    xyz_order = ["X", "Y", "Z", "No demand"]

    matrix = pd.crosstab(df["ABC"], df["XYZ"])
    matrix = matrix.reindex(index=abc_order, columns=xyz_order, fill_value=0)

    values = matrix.to_numpy()
    fig, ax = plt.subplots(figsize=(8.5, 5.5))

    image = ax.imshow(values, cmap="Blues", aspect="auto")
    ax.set_xticks(np.arange(len(xyz_order)), labels=xyz_order)
    ax.set_yticks(np.arange(len(abc_order)), labels=abc_order)
    ax.set_xlabel("XYZ class – demand variability", labelpad=12)
    ax.set_ylabel("ABC class – contribution to dispensing events", labelpad=12)
    ax.set_title(
        "ABC × XYZ product matrix",
        fontsize=16,
        color=NAVY,
        fontweight="bold",
        pad=18,
    )

    threshold = values.max() / 2 if values.size else 0
    for row in range(values.shape[0]):
        for col in range(values.shape[1]):
            value = int(values[row, col])
            ax.text(
                col,
                row,
                f"{value}\nproducts",
                ha="center",
                va="center",
                color=WHITE if value > threshold else DARK,
                fontsize=11,
                fontweight="bold",
            )

    colorbar = fig.colorbar(image, ax=ax, shrink=0.82)
    colorbar.set_label("Number of products")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.text(
        0.5,
        0.015,
        "No-demand products are displayed separately from X, Y and Z.",
        ha="center",
        fontsize=9,
        color=GREY,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save_figure(fig, output_dir / "abc_xyz_heatmap.png")


# ---------------------------------------------------------------------
# FIGURE 3: COMBINED ABC × XYZ × FSN PROFILES
# ---------------------------------------------------------------------

def plot_combined_classifications(
    df: pd.DataFrame,
    output_dir: Path,
) -> None:
    combined = (
        df.assign(profile=df["ABC"] + "-" + df["XYZ"] + "-" + df["FSN"])
        ["profile"]
        .value_counts()
        .head(12)
        .sort_values(ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 6.5))
    bars = ax.barh(
        combined.index,
        combined.values,
        color=[BLUE if value != combined.max() else NAVY for value in combined.values],
        height=0.68,
    )

    ax.set_title(
        "Most frequent combined classification profiles",
        fontsize=16,
        color=NAVY,
        fontweight="bold",
        pad=16,
    )
    ax.set_xlabel("Number of products")
    ax.set_ylabel("ABC – XYZ – FSN profile")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="x", color=LIGHT_GREY, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlim(0, max(combined.values) * 1.16)

    for bar, value in zip(bars, combined.values):
        ax.text(
            value + max(combined.values) * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{int(value)}",
            va="center",
            fontsize=9,
            fontweight="bold",
        )

    fig.text(
        0.5,
        0.015,
        "Top 12 profiles by product count. The remaining profiles are not shown.",
        ha="center",
        fontsize=9,
        color=GREY,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save_figure(fig, output_dir / "combined_classifications.png")


# ---------------------------------------------------------------------
# FIGURE 4: ATC5 MATCHING COVERAGE
# ---------------------------------------------------------------------

def plot_atc5_coverage(df: pd.DataFrame, output_dir: Path) -> None:
    matched = int(df["ATC_code"].notna().sum())
    unmatched = int(df["ATC_code"].isna().sum())
    total = len(df)
    coverage = matched / total * 100 if total else 0

    fig, ax = plt.subplots(figsize=(7.5, 5))
    values = [matched, unmatched]
    labels = ["ATC5 matched", "Not matched"]
    colors = [NAVY, LIGHT_GREY]

    bars = ax.bar(labels, values, color=colors, width=0.55)
    ax.set_title(
        "ATC5 mapping coverage",
        fontsize=16,
        color=NAVY,
        fontweight="bold",
        pad=16,
    )
    ax.set_ylabel("Number of monitored products")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="y", color=LIGHT_GREY, linewidth=0.8)
    ax.set_axisbelow(True)
    add_bar_labels(ax, bars, values)

    for bar, value in zip(bars, values):
        percentage = value / total * 100 if total else 0
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 0.55,
            f"{percentage:.1f}%",
            ha="center",
            va="center",
            color=WHITE if value == matched else DARK,
            fontweight="bold",
            fontsize=11,
        )

    fig.text(
        0.5,
        0.02,
        f"{matched} of {total} products mapped | ATC5 coverage: {coverage:.2f}%",
        ha="center",
        fontsize=10,
        color=GREY,
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save_figure(fig, output_dir / "atc5_coverage.png")


# ---------------------------------------------------------------------
# FIGURE 5: MOST FREQUENT ATC5 CODES
# ---------------------------------------------------------------------

def plot_top_atc5_codes(
    df: pd.DataFrame,
    output_dir: Path,
    top_n: int = 15,
) -> None:
    mapped = df.dropna(subset=["ATC_code"])
    counts = (
        mapped["ATC_code"]
        .value_counts()
        .head(top_n)
        .sort_values(ascending=True)
    )

    if counts.empty:
        LOGGER.warning("No ATC5 codes available; skipping top ATC5 chart.")
        return

    fig, ax = plt.subplots(figsize=(9, 7))
    bars = ax.barh(counts.index, counts.values, color=BLUE, height=0.68)

    ax.set_title(
        f"Most frequent ATC5 codes among monitored products",
        fontsize=15,
        color=NAVY,
        fontweight="bold",
        pad=16,
    )
    ax.set_xlabel("Number of monitored products")
    ax.set_ylabel("ATC5 code")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="x", color=LIGHT_GREY, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlim(0, max(counts.values) * 1.18)

    for bar, value in zip(bars, counts.values):
        ax.text(
            value + max(counts.values) * 0.02,
            bar.get_y() + bar.get_height() / 2,
            str(int(value)),
            va="center",
            fontsize=9,
            fontweight="bold",
        )

    fig.text(
        0.5,
        0.015,
        "ATC5 codes are shown as identifiers; this chart does not group products by therapeutic class.",
        ha="center",
        fontsize=8.5,
        color=GREY,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save_figure(fig, output_dir / "top_atc5_codes.png")


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    apply_style()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Loading classification data from: %s", args.data_dir)
    products = load_data(args.data_dir)

    LOGGER.info("Generating figures in: %s", args.output_dir)

    plot_classification_distributions(products, args.output_dir)
    plot_abc_xyz_heatmap(products, args.output_dir)
    plot_combined_classifications(products, args.output_dir)
    plot_atc5_coverage(products, args.output_dir)
    plot_top_atc5_codes(products, args.output_dir)

    LOGGER.info("All available figures have been generated.")
    LOGGER.info("Monitored products: %s", len(products))
    LOGGER.info(
        "ATC5 coverage: %s/%s (%.2f%%)",
        products["ATC_code"].notna().sum(),
        len(products),
        products["ATC_code"].notna().mean() * 100,
    )


if __name__ == "__main__":
    main()
