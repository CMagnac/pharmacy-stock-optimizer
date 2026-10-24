
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

REGISTRY_PATH = DATA / "monitored_product_registry.csv"
BILLING_PATH = DATA / "billing_history_clean.parquet"

OUTPUT_PATH = DATA / "monthly_event_demand_nov2025_sep2026.parquet"

START_MONTH = "2025-11"
END_MONTH = "2026-09"


def main() -> None:
    registry = pd.read_csv(
        REGISTRY_PATH,
        dtype={"product_code": "string"},
        keep_default_na=False,
    )
    billing = pd.read_parquet(BILLING_PATH)

    for frame in (registry, billing):
        frame["product_code"] = (
            frame["product_code"].astype("string").str.strip()
        )

    if registry["product_code"].duplicated().any():
        raise ValueError("Duplicate product codes found in registry.")

    billing["transaction_date"] = pd.to_datetime(
        billing["transaction_date"], errors="raise"
    )
    billing["quantity_dispensed"] = pd.to_numeric(
        billing["quantity_dispensed"], errors="raise"
    )

    # Keep only products in the monitored registry.
    billing = billing[
        billing["product_code"].isin(registry["product_code"])
    ].copy()

    billing["month"] = (
        billing["transaction_date"].dt.to_period("M").astype(str)
    )

    # Keep only complete calendar months.
    billing = billing[
        billing["month"].between(START_MONTH, END_MONTH)
    ].copy()

    # One row per product/month, counting dispensing transactions,
    # not the number of boxes dispensed.
    observed = (
        billing.groupby(["product_code", "month"], as_index=False)
        .agg(
            dispensing_events=("quantity_dispensed", "size"),
            boxes_dispensed=("quantity_dispensed", "sum"),
        )
    )

    months = pd.period_range(
        START_MONTH, END_MONTH, freq="M"
    ).astype(str)

    grid = pd.MultiIndex.from_product(
        [registry["product_code"].tolist(), months],
        names=["product_code", "month"],
    ).to_frame(index=False)

    monthly = grid.merge(
        observed,
        on=["product_code", "month"],
        how="left",
        validate="one_to_one",
    )

    monthly["dispensing_events"] = (
        monthly["dispensing_events"].fillna(0).astype("int64")
    )
    monthly["boxes_dispensed"] = (
        monthly["boxes_dispensed"].fillna(0)
    )

    monthly = monthly.merge(
        registry[["product_code", "designation"]],
        on="product_code",
        how="left",
        validate="many_to_one",
    )

    monthly = monthly[
        [
            "product_code",
            "designation",
            "month",
            "dispensing_events",
            "boxes_dispensed",
        ]
    ].sort_values(["product_code", "month"])

    if monthly.duplicated(["product_code", "month"]).any():
        raise ValueError("Duplicate product-month rows found.")

    expected_rows = len(registry) * len(months)
    if len(monthly) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} rows, found {len(monthly)}."
        )

    # Reconcile the event counts against the source billing records.
    expected_events = len(billing)
    actual_events = int(monthly["dispensing_events"].sum())

    if expected_events != actual_events:
        raise ValueError(
            "Event reconciliation failed: "
            f"billing={expected_events}, monthly={actual_events}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_parquet(OUTPUT_PATH, index=False)

    print("MONTHLY DISPENSING-EVENT DEMAND")
    print("=" * 45)
    print(f"Registered products: {len(registry):,}")
    print(f"Months: {START_MONTH} to {END_MONTH}")
    print(f"Expected rows: {expected_rows:,}")
    print(f"Actual rows: {len(monthly):,}")
    print(f"Source dispensing records: {expected_events:,}")
    print(f"Monthly dispensing events: {actual_events:,}")
    print(f"Total boxes (reference only): "
          f"{monthly['boxes_dispensed'].sum():,.0f}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
