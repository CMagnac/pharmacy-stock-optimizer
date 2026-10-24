
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

REGISTRY_PATH = DATA / "monitored_product_registry.csv"
BILLING_PATH = DATA / "billing_history_clean.parquet"
DEMAND_PATH = DATA / "monthly_demand_monitored.parquet"


def load_data():
    registry = pd.read_csv(
        REGISTRY_PATH,
        dtype={"product_code": "string"},
        keep_default_na=False,
    )
    billing = pd.read_parquet(BILLING_PATH)
    demand = pd.read_parquet(DEMAND_PATH)

    for frame in (registry, billing, demand):
        frame["product_code"] = (
            frame["product_code"].astype("string").str.strip()
        )

    registry["analysis_start_month"] = registry[
        "analysis_start_month"
    ].astype("string").str.strip()

    registry["analysis_end_month"] = registry[
        "analysis_end_month"
    ].astype("string").str.strip()

    billing["transaction_date"] = pd.to_datetime(
        billing["transaction_date"], errors="raise"
    )
    billing["quantity_dispensed"] = pd.to_numeric(
        billing["quantity_dispensed"], errors="raise"
    )
    demand["quantity_dispensed"] = pd.to_numeric(
        demand["quantity_dispensed"], errors="raise"
    )

    billing["month"] = (
        billing["transaction_date"].dt.to_period("M").astype(str)
    )
    demand["month"] = demand["month"].astype(str)

    return registry, billing, demand


def validate_reconciliation(registry, billing, demand):
    print("\nVALIDATION 1 — RECONCILIATION")
    print("=" * 50)

    if registry["product_code"].duplicated().any():
        raise ValueError("Duplicate product codes found in registry.")

    if demand.duplicated(["product_code", "month"]).any():
        raise ValueError("Duplicate product-month rows in demand data.")

    if (billing["quantity_dispensed"] < 0).any():
        raise ValueError("Negative dispensing quantities found in billing.")

    # Keep billing records for registered products only.
    expected = billing.merge(
        registry[
            ["product_code", "analysis_start_month", "analysis_end_month"]
        ],
        on="product_code",
        how="inner",
        validate="many_to_one",
    )

    # Apply each product's analysis period.
    expected = expected[
        expected["month"] >= expected["analysis_start_month"]
    ]

    has_end_month = expected["analysis_end_month"] != ""
    expected = expected[
        ~has_end_month
        | (expected["month"] <= expected["analysis_end_month"])
    ]

    expected_by_month = (
        expected.groupby(["product_code", "month"], as_index=False)
        ["quantity_dispensed"]
        .sum()
        .rename(columns={"quantity_dispensed": "expected_boxes"})
    )

    actual_by_month = (
        demand.groupby(["product_code", "month"], as_index=False)
        ["quantity_dispensed"]
        .sum()
        .rename(columns={"quantity_dispensed": "actual_boxes"})
    )

    comparison = expected_by_month.merge(
        actual_by_month,
        on=["product_code", "month"],
        how="outer",
    ).fillna({"expected_boxes": 0, "actual_boxes": 0})

    comparison["difference"] = (
        comparison["actual_boxes"] - comparison["expected_boxes"]
    )

    mismatches = comparison[comparison["difference"].abs() > 1e-9]

    expected_total = expected["quantity_dispensed"].sum()
    actual_total = demand["quantity_dispensed"].sum()

    print(f"Expected boxes from billing: {expected_total:,.0f}")
    print(f"Boxes in monthly demand:     {actual_total:,.0f}")
    print(f"Difference:                  {actual_total - expected_total:,.0f}")
    print(f"Product-month mismatches:     {len(mismatches)}")

    if mismatches.empty and abs(actual_total - expected_total) < 1e-9:
        print("PASS: Demand totals reconcile with billing.")
    else:
        print("FAIL: Investigate the mismatches before proceeding.")
        print(mismatches.head(20).to_string(index=False))

    return mismatches.empty and abs(actual_total - expected_total) < 1e-9


def validate_zero_demand(registry, demand):
    print("\nVALIDATION 2 — ZERO-DEMAND PRODUCTS")
    print("=" * 50)

    totals = (
        demand.groupby("product_code")["quantity_dispensed"]
        .sum()
        .reindex(registry["product_code"], fill_value=0)
    )

    zero_products = totals[totals == 0]
    active_products = totals[totals > 0]

    print(f"Registered products:         {len(registry):,}")
    print(f"Products with demand:        {len(active_products):,}")
    print(f"Products with zero demand:   {len(zero_products):,}")

    if len(zero_products):
        zero_report = registry[
            registry["product_code"].isin(zero_products.index)
        ][["product_code", "designation"]].copy()

        zero_report["total_boxes"] = 0

        print("\nFirst 20 zero-demand products:")
        print(zero_report.head(20).to_string(index=False))

    print(
        "\nNote: zero recorded demand does not necessarily mean "
        "the product is unnecessary."
    )


def validate_demand_distribution(registry, demand):
    print("\nVALIDATION 3 — DEMAND DISTRIBUTION")
    print("=" * 50)

    totals = (
        demand.groupby("product_code", as_index=False)
        .agg(
            total_boxes=("quantity_dispensed", "sum"),
            active_months=("quantity_dispensed", lambda s: (s > 0).sum()),
        )
    )

    totals = totals.merge(
        registry[["product_code", "designation"]],
        on="product_code",
        how="left",
        validate="one_to_one",
    )

    print("\nTop 10 products by boxes dispensed:")
    print(
        totals.sort_values("total_boxes", ascending=False)
        [["product_code", "designation", "total_boxes", "active_months"]]
        .head(10)
        .to_string(index=False)
    )

    monthly = (
        demand.groupby("month", as_index=False)
        .agg(
            boxes_dispensed=("quantity_dispensed", "sum"),
            products_with_demand=(
                "quantity_dispensed",
                lambda s: (s > 0).sum(),
            ),
        )
        .sort_values("month")
    )

    monthly["partial_month"] = monthly["month"].isin(
        ["2025-10", "2026-10"]
    )

    print("\nMonthly demand:")
    print(monthly.to_string(index=False))

    print(
        "\nReminder: October 2025 and October 2026 are partial months. "
        "Do not compare their raw totals directly with complete months."
    )


def main():
    registry, billing, demand = load_data()

    print("MONTHLY DEMAND VALIDATION")
    print("=" * 50)

    print(f"Registry products: {len(registry):,}")
    print(f"Demand rows:       {len(demand):,}")
    print(f"Billing rows:      {len(billing):,}")

    validate_reconciliation(registry, billing, demand)
    validate_zero_demand(registry, demand)
    validate_demand_distribution(registry, demand)


if __name__ == "__main__":
    main()
