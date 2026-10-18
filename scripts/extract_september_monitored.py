from pathlib import Path

import pandas as pd


AUGUST_FILE = Path(
    "data/processed/inventory_2026_08.parquet"
)

SEPTEMBER_FILE = Path(
    "data/processed/full_inventory_2026_09_clean.parquet"
)

OUTPUT_FILE = Path(
    "data/processed/inventory_2026_09_monitored.parquet"
)


SNAPSHOT_COLUMNS = [
    "product_code",
    "designation",
    "inventory_date",
    "stock_before",
    "stock_after",
    "stock_difference",
    "net_purchase_price",
    "difference_value",
    "stock_value",
    "absolute_difference_value",
    "observation_status",
]


def main():
    print("Extracting September monitored inventory")
    print("=========================================")

    # Load August monitored population
    august = pd.read_parquet(AUGUST_FILE)

    # Load complete September inventory
    september = pd.read_parquet(SEPTEMBER_FILE)

    # Keep only the August monitored product codes
    monitored_codes = (
        august["product_code"]
        .dropna()
        .astype(str)
        .unique()
    )

    # Extract September products belonging to monitored population
    september_monitored = september[
        september["product_code"]
        .astype(str)
        .isin(monitored_codes)
    ][SNAPSHOT_COLUMNS].copy()

    # Keep the complete August monitoring population
    monitored_products = (
        august[
            [
                "product_code",
                "designation",
            ]
        ]
        .drop_duplicates("product_code")
        .copy()
    )

    # Left join:
    # every August monitored product remains present
    september_snapshot = monitored_products.merge(
        september_monitored,
        on="product_code",
        how="left",
        suffixes=("_august", ""),
    )
    # Identify whether the product was observed in September
    september_snapshot["observation_status"] = (
        september_snapshot["inventory_date"]
        .notna()
        .map({
            True: "observed",
            False: "missing",
        })
    )
    # If a product is absent from September,
    # keep its August designation.
    september_snapshot["designation"] = (
        september_snapshot["designation"]
        .fillna(september_snapshot["designation_august"])
    )

    september_snapshot = (
        september_snapshot
        .drop(columns=["designation_august"])
        .sort_values("product_code")
        .reset_index(drop=True)
    )

    # Save
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    september_snapshot.to_parquet(
        OUTPUT_FILE,
        index=False,
    )

    # Statistics
    total = len(september_snapshot)

    found = september_snapshot["inventory_date"].notna().sum()

    missing = total - found

    print("\nSeptember monitored snapshot")
    print("----------------------------")
    print(f"Monitored products: {total}")
    print(f"Found in September: {found}")
    print(f"Not found: {missing}")

    print("\nSaved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
