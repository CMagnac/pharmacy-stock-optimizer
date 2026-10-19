from pathlib import Path
import argparse

import pandas as pd


REQUIRED_COLUMNS = [
    "Code produit",
    "Date",
    "Stock avant",
    "Stock modifié",
    "Ecart",
    "Module",
]

NUMERIC_COLUMNS = [
    "Stock avant",
    "Stock modifié",
    "Ecart",
    "PAMP net",
    "Ecart en PAMP net",
    "Dernier PA net remisé",
    "Ecart en dernier PA net remisé",
]


def load_billing_history(file_path: Path) -> pd.DataFrame:
    """Load the billing CSV without modifying the source file."""

    df = pd.read_csv(
        file_path,
        sep=";",
        encoding="cp1252",
        decimal=",",
        dtype={"Code produit": "string"},
        low_memory=False,
    )

    # Normalize column names, including common encoding artifacts.
    df.columns = (
        df.columns
        .str.strip()
        .str.replace("Dï¿½signation", "Désignation", regex=False)
        .str.replace("Code opï¿½rateur", "Code opérateur", regex=False)
        .str.replace("Stock modifiï¿½", "Stock modifié", regex=False)
        .str.replace("remisï¿½", "remisé", regex=False)
    )

    # Parse dates using the format shown in the sample.
    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%d/%m/%Y %H:%M",
        errors="coerce",
    )

    # Convert numerical columns explicitly.
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            values = (
                df[column]
                .astype("string")
                .str.strip()
                .str.replace(",", ".", regex=False)
            )

            df[column] = pd.to_numeric(
                values,
                errors="coerce",
            )

    return df

def inspect_history(df: pd.DataFrame) -> None:
    """Print a data-quality and structure report."""

    print("\nBILLING HISTORY INSPECTION")
    print("=" * 60)

    print(f"Total rows: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Unique product codes: {df['Code produit'].nunique():,}")
    print(
        "Missing product codes: "
        f"{df['Code produit'].isna().sum():,}"
    )

    valid_dates = df["Date"].dropna()

    print("\nDATE RANGE")
    print("-" * 60)

    if valid_dates.empty:
        print("No valid dates found.")
    else:
        print(f"Earliest date: {valid_dates.min()}")
        print(f"Latest date:   {valid_dates.max()}")
        print(f"Invalid dates: {df['Date'].isna().sum():,}")

        print("\nRows per month:")
        print(
            valid_dates.dt.to_period("M")
            .value_counts()
            .sort_index()
            .to_string()
        )

    print("\nMODULES")
    print("-" * 60)
    print(df["Module"].value_counts(dropna=False).to_string())

    if "Code opérateur" in df.columns:
        print("\nOPERATORS")
        print("-" * 60)
        print(
            df["Code opérateur"]
            .value_counts(dropna=False)
            .to_string()
        )

    print("\nMISSING VALUES")
    print("-" * 60)

    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)

    if missing.empty:
        print("No missing values.")
    else:
        print(missing.to_string())

    print("\nDUPLICATE ROWS")
    print("-" * 60)
    print(f"Exact duplicate rows: {df.duplicated().sum():,}")

    print("\nSTOCK ARITHMETIC")
    print("-" * 60)

    required_numeric = [
        "Stock avant",
        "Stock modifié",
        "Ecart",
    ]

    if all(column in df.columns for column in required_numeric):
        valid = df[required_numeric].notna().all(axis=1)

        calculated_difference = (
            df.loc[valid, "Stock modifié"]
            - df.loc[valid, "Stock avant"]
        )

        reported_difference = df.loc[valid, "Ecart"]

        mismatch = ~(
            (calculated_difference - reported_difference).abs()
            < 0.000001
        )

        print(f"Rows checked: {valid.sum():,}")
        print(f"Rows with arithmetic mismatch: {mismatch.sum():,}")
        print(
            "Rows excluded due to missing numeric values: "
            f"{(~valid).sum():,}"
        )

    print("\nECART DISTRIBUTION")
    print("-" * 60)

    ecart = df["Ecart"].dropna()

    if ecart.empty:
        print("No valid Ecart values found.")
    else:
        print(f"Negative movements: {(ecart < 0).sum():,}")
        print(f"Zero movements:     {(ecart == 0).sum():,}")
        print(f"Positive movements: {(ecart > 0).sum():,}")
        print(f"Minimum Ecart: {ecart.min()}")
        print(f"Maximum Ecart: {ecart.max()}")

    print("\nINSPECTION COMPLETE")
    print("The source CSV has not been modified.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect a pharmacy billing-history CSV."
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to the billing-history CSV file",
    )
    args = parser.parse_args()

    if not args.file.is_file():
        raise FileNotFoundError(
            f"Billing CSV not found: {args.file}"
        )

    df = load_billing_history(args.file)
    inspect_history(df)


if __name__ == "__main__":
    main()
