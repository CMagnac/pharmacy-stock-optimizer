
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "inventory_2026_08.parquet"
OUTPUT = ROOT / "data" / "processed" / "monitored_product_registry.csv"


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(
            f"{OUTPUT} already exists. Refusing to overwrite the registry."
        )

    inventory = pd.read_parquet(SOURCE)

    required = {"product_code", "designation"}
    missing = required - set(inventory.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    registry = inventory[["product_code", "designation"]].copy()
    registry["product_code"] = registry["product_code"].astype("string").str.strip()
    registry["designation"] = registry["designation"].astype("string").str.strip()

    registry = registry.dropna(subset=["product_code"])
    registry = registry[registry["product_code"] != ""]
    registry = registry.drop_duplicates(subset=["product_code"])

    # Keep the original products eligible for historical demand analysis.
    # This allows the one-year billing history to be used, not just August onward.
    registry["category"] = "unclassified"
    registry["analysis_start_month"] = "2025-10"
    registry["analysis_end_month"] = ""
    registry["monitoring_start_month"] = "2026-08"
    registry["monitoring_end_month"] = ""

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    registry.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

    print("MONITORED PRODUCT REGISTRY")
    print("=" * 40)
    print(f"Products: {len(registry)}")
    print(f"Output: {OUTPUT}")
    print("\nCategories to classify:")
    print(registry["category"].value_counts().to_string())
    print("\nEdit the category column in the CSV when ready.")


if __name__ == "__main__":
    main()
