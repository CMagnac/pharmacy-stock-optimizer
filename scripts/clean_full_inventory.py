from pathlib import Path
import pandas as pd


INPUT_FILE = Path(
    "data/processed/full_inventory_2026_09.parquet"
)

OUTPUT_FILE = Path(
    "data/processed/full_inventory_2026_09_clean.parquet"
)


def main():
    df = pd.read_parquet(INPUT_FILE)

    print("Cleaning September full inventory")
    print("==================================")

    initial_rows = len(df)

    # 1. Remove rows without a product code
    missing_code_mask = df["product_code"].isna()
    missing_code_count = int(missing_code_mask.sum())

    df = df[~missing_code_mask].copy()

    print(f"Rows with missing product code removed: {missing_code_count}")

    # 2. Remove duplicate product codes
    duplicate_mask = df["product_code"].duplicated(keep="first")
    duplicate_count = int(duplicate_mask.sum())

    df = df[~duplicate_mask].copy()

    print(f"Duplicate product rows removed: {duplicate_count}")

    # 3. Save cleaned dataset
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_FILE, index=False)

    print("\nCleaning summary")
    print("----------------")
    print(f"Initial rows: {initial_rows}")
    print(f"Final rows: {len(df)}")
    print(f"Rows removed: {initial_rows - len(df)}")
    print(f"Unique products: {df['product_code'].nunique()}")

    print(f"\nSaved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
