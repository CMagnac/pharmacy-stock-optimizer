
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BILLING_PATH = ROOT / "data" / "processed" / "billing_history_clean.parquet"
REGISTRY_PATH = ROOT / "data" / "processed" / "monitored_product_registry.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "monthly_demand_monitored.parquet"
SUMMARY_PATH = ROOT / "data" / "processed" / "monthly_demand_summary.parquet"


def month_period(values: pd.Series) -> pd.PeriodIndex:
    return pd.PeriodIndex(pd.to_datetime(values).dt.to_period("M"), freq="M")


def main() -> None:
    billing = pd.read_parquet(BILLING_PATH)
    registry = pd.read_csv(
        REGISTRY_PATH,
        dtype={
            "product_code": "string",
            "analysis_start_month": "string",
            "analysis_end_month": "string",
        },
        keep_default_na=False,
    )

    billing_required = {
        "transaction_date",
        "product_code",
        "quantity_dispensed",
    }
    registry_required = {
        "product_code",
        "designation",
        "category",
        "analysis_start_month",
        "analysis_end_month",
    }

    missing_billing = billing_required - set(billing.columns)
    missing_registry = registry_required - set(registry.columns)

    if missing_billing:
        raise ValueError(
            f"Billing dataset is missing columns: {sorted(missing_billing)}"
        )
    if missing_registry:
        raise ValueError(
            f"Registry is missing columns: {sorted(missing_registry)}"
        )

    # Normalize join keys without converting product codes to numbers.
    billing["product_code"] = billing["product_code"].astype("string").str.strip()
    registry["product_code"] = registry["product_code"].astype("string").str.strip()

    if registry["product_code"].isna().any() or registry["product_code"].eq("").any():
        raise ValueError("Registry contains missing or empty product codes.")

    if registry["product_code"].duplicated().any():
        duplicates = registry.loc[
            registry["product_code"].duplicated(keep=False), "product_code"
        ].tolist()
        raise ValueError(f"Registry has duplicate product codes: {duplicates[:10]}")

    billing["transaction_date"] = pd.to_datetime(
        billing["transaction_date"], errors="coerce"
    )
    billing["quantity_dispensed"] = pd.to_numeric(
        billing["quantity_dispensed"], errors="coerce"
    )

    billing = billing.dropna(
        subset=["transaction_date", "product_code", "quantity_dispensed"]
    )
    billing = billing[billing["product_code"] != ""]

    if billing.empty:
        raise ValueError("No valid billing records remain after validation.")

    # The cleaned source should already contain dispensed quantities only.
    if (billing["quantity_dispensed"] < 0).any():
        raise ValueError(
            "quantity_dispensed contains negative values. "
            "Check the cleaning pipeline before proceeding."
        )

    billing["month"] = billing["transaction_date"].dt.to_period("M").astype(str)

    # Aggregate the cleaned billing history before joining it to the registry.
    monthly = (
        billing.groupby(["product_code", "month"], as_index=False)
        .agg(
            quantity_dispensed=("quantity_dispensed", "sum"),
            dispensing_transactions=("quantity_dispensed", "size"),
        )
    )

    # Parse registry analysis periods.
    registry["analysis_start_month"] = registry["analysis_start_month"].str.strip()
    registry["analysis_end_month"] = registry["analysis_end_month"].str.strip()

    if registry["analysis_start_month"].eq("").any():
        raise ValueError("Every registry product needs an analysis_start_month.")

    registry["start_period"] = registry["analysis_start_month"].map(
        lambda value: pd.Period(value, freq="M")
    )
    registry["end_period"] = registry["analysis_end_month"].map(
        lambda value: pd.Period(value, freq="M") if value else pd.NaT
    )

    first_month = billing["transaction_date"].min().to_period("M")
    last_month = billing["transaction_date"].max().to_period("M")
    all_months = pd.period_range(first_month, last_month, freq="M")

    # Generate only the months during which each product is in its analysis range.
    grids = []
    for row in registry.itertuples(index=False):
        start = max(row.start_period, first_month)
        end = last_month

        if not pd.isna(row.end_period):
            end = min(row.end_period, last_month)

        if start > end:
            continue

        grids.append(
            pd.DataFrame(
                {
                    "product_code": row.product_code,
                    "month": [str(month) for month in pd.period_range(
                        start, end, freq="M"
                    )],
                }
            )
        )

    if not grids:
        raise ValueError("No product analysis periods overlap the billing history.")

    demand = pd.concat(grids, ignore_index=True)
    demand = demand.merge(
        registry[
            ["product_code", "designation", "category"]
        ],
        on="product_code",
        how="left",
        validate="many_to_one",
    )
    demand = demand.merge(
        monthly,
        on=["product_code", "month"],
        how="left",
        validate="one_to_one",
    )

    demand["quantity_dispensed"] = demand["quantity_dispensed"].fillna(0)
    demand["dispensing_transactions"] = (
        demand["dispensing_transactions"].fillna(0).astype("int64")
    )

    # Flag the incomplete boundary months of the billing dataset.
    first_date = billing["transaction_date"].min()
    last_date = billing["transaction_date"].max()
    demand["month_start"] = pd.PeriodIndex(demand["month"], freq="M").to_timestamp()
    demand["month_end"] = (
        pd.PeriodIndex(demand["month"], freq="M").to_timestamp(how="end").normalize()
    )
    demand["partial_month"] = (
        (demand["month_start"] < first_date.normalize())
        | (demand["month_end"] > last_date.normalize())
    )

    demand = demand.drop(columns=["month_start", "month_end"])
    demand = demand.sort_values(["product_code", "month"]).reset_index(drop=True)

    # Product-level summary. Partial months are flagged in the source series
    # and should be considered separately when interpreting averages.
    summary = (
        demand.groupby(["product_code", "designation", "category"], as_index=False)
        .agg(
            total_boxes_dispensed=("quantity_dispensed", "sum"),
            average_monthly_demand=("quantity_dispensed", "mean"),
            monthly_demand_std=("quantity_dispensed", "std"),
            months_in_analysis=("month", "nunique"),
            active_months=("quantity_dispensed", lambda values: int((values > 0).sum())),
            dispensing_transactions=("dispensing_transactions", "sum"),
        )
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    demand.to_parquet(OUTPUT_PATH, index=False)
    summary.to_parquet(SUMMARY_PATH, index=False)

    print("MONTHLY DEMAND ANALYSIS")
    print("=" * 40)
    print(f"Registry products: {len(registry)}")
    print(f"Billing records used: {len(billing):,}")
    print(f"Product-month rows: {len(demand):,}")
    print(f"Products in demand output: {demand['product_code'].nunique():,}")
    print(f"Total boxes dispensed: {demand['quantity_dispensed'].sum():,.0f}")
    print(f"Months covered: {demand['month'].min()} to {demand['month'].max()}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Summary: {SUMMARY_PATH}")
    print("\nBoundary months flagged as partial:")
    print(
        demand.loc[demand["partial_month"], "month"]
        .drop_duplicates()
        .sort_values()
        .to_list()
    )


if __name__ == "__main__":
    main()
