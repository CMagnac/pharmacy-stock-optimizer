from pathlib import Path

from pharmacy_stock.pipeline import process_inventory


INPUT_FILE = Path(
    "data/raw/inventory_2026_08.csv"
)

OUTPUT_FILE = Path(
    "data/processed/inventory_2026_08.parquet"
)


def main():
    print("Starting inventory processing...")

    df, report = process_inventory(INPUT_FILE)

    print("\nInventory validation report")
    print("===========================")

    for key, value in report.items():
        print(f"{key}: {value}")

    # Create output directory if necessary
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save processed dataset
    df.to_parquet(
        OUTPUT_FILE,
        index=False,
    )

    print("\nProcessed dataset")
    print("=================")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nFirst rows:")
    print(df.head())


if __name__ == "__main__":
    main()
