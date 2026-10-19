"""Clean the pharmacy billing history for demand analysis."""

from pathlib import Path
import argparse

import pandas as pd


# Expected input columns after header normalization.
REQUIRED_COLUMNS = [
    "Code produit",
    "Désignation",
    "Date",
    "Ecart",
]

COLUMN_RENAMES = {
    "Code produit": "product_code",
    "Désignation": "designation",
    "Date": "transaction_date",
    "Ecart": "stock_movement",
}


def load_billing_history(filepath: Path) -> pd.DataFrame:
    """Load the original billing CSV without modifying the source file."""
    df = pd.read_csv(
        filepath,
        sep=";",
        encoding="cp1252",
        dtype=str,
    )

    # Normalize known encoding artifacts in the column names.
    df.columns = (
        df.columns
        .str.strip()
        .str.replace("Dï¿½signation", "Désignation", regex=False)
        .str.replace("Code opï¿½rateur", "Code opérateur", regex=False)
        .str.replace("Stock modifiï¿½", "Stock modifié", regex=False)
        .str.replace("remisï¿½", "remisé", regex=False)
    )

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}. "
            f"Available columns: {df.columns.tolist()}"
        )

    return df

def clean_billing_history(df: pd.DataFrame) -> pd.DataFrame:
    """Keep dispensing movements, remove exact duplicates, and prepare the dataset."""
    df = df.copy()

    # Normalize product codes and designations.
    df["Code produit"] = df["Code produit"].str.strip()
    df["Désignation"] = df["Désignation"].str.strip()

    # Remove rows without a usable product code.
    df = df[
        df["Code produit"].notna()
        & df["Code produit"].ne("")
    ].copy()

    # Parse dates and French decimal-comma movement values.
    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%d/%m/%Y %H:%M",
        errors="coerce",
    )

    movement = (
        df["Ecart"]
        .astype("string")
        .str.strip()
        .str.replace(",", ".", regex=False)
    )

    df["Ecart"] = pd.to_numeric(movement, errors="coerce")

    # Keep only valid, negative stock movements.
    df = df[
        df["Ecart"].notna()
        & df["Ecart"].lt(0)
    ].copy()

    # Remove exact duplicate rows across all original columns.
    rows_before_deduplication = len(df)
    df = df.drop_duplicates().copy()
    duplicates_removed = rows_before_deduplication - len(df)

    # Convert negative movements to positive dispensed quantities.
    df["quantity_dispensed"] = -df["Ecart"]

    # Rename columns for analysis.
    df = df.rename(columns=COLUMN_RENAMES)

    # Keep the fields needed for demand analysis.
    df = df[
        [
            "transaction_date",
            "product_code",
            "designation",
            "stock_movement",
            "quantity_dispensed",
        ]
    ].copy()

    df = df.sort_values(
        ["transaction_date", "product_code"],
        ignore_index=True,
    )

    print(f"Exact duplicate rows removed: {duplicates_removed:,}")

    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean pharmacy billing history for demand analysis."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="data/raw/full_one_year_billing_2025_2026.csv",
        help="Path to the source billing CSV.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/billing_history_clean.parquet",
        help="Path to the output Parquet file.",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}"
        )

    original_df = load_billing_history(input_path)
    cleaned_df = clean_billing_history(original_df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_df.to_parquet(output_path, index=False)

    print("\nBILLING HISTORY CLEANING")
    print("=" * 50)
    print(f"Original rows: {len(original_df):,}")
    print(f"Cleaned rows: {len(cleaned_df):,}")
    print(
        f"Rows removed: "
        f"{len(original_df) - len(cleaned_df):,}"
    )
    print(
        f"Unique products: "
        f"{cleaned_df['product_code'].nunique():,}"
    )

    if not cleaned_df.empty:
        print(
            f"Date range: "
            f"{cleaned_df['transaction_date'].min()} "
            f"to {cleaned_df['transaction_date'].max()}"
        )
        print(
            f"Total boxes dispensed: "
            f"{cleaned_df['quantity_dispensed'].sum():,.0f}"
        )

    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
