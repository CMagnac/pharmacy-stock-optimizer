
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

INPUT_PATH = DATA / "monthly_event_demand_nov2025_sep2026.parquet"
OUTPUT_PATH = DATA / "demand_classifications_nov2025_sep2026.parquet"
MONTHLY_SUMMARY_PATH = DATA / "monthly_event_demand_summary_nov2025_sep2026.csv"

# Configurable thresholds
ABC_A_LIMIT = 0.80
ABC_B_LIMIT = 0.95

XYZ_X_MAX_CV = 0.50
XYZ_Y_MAX_CV = 1.00

FSN_F_MIN_MONTHS = 9
FSN_S_MIN_MONTHS = 4


def classify_abc(product_summary: pd.DataFrame) -> pd.Series:
    """Classify products by cumulative share of dispensing events."""
    total_events = product_summary["total_events"].sum()

    if total_events == 0:
        return pd.Series("C", index=product_summary.index)

    ranked = product_summary.sort_values(
        ["total_events", "product_code"],
        ascending=[False, True],
    ).copy()

    ranked["event_share"] = ranked["total_events"] / total_events
    ranked["cumulative_share"] = ranked["event_share"].cumsum()

    # Class based on cumulative share, including the product
    # that crosses each threshold.
    ranked["ABC"] = np.select(
        [
            ranked["cumulative_share"] - ranked["event_share"] < ABC_A_LIMIT,
            ranked["cumulative_share"] - ranked["event_share"] < ABC_B_LIMIT,
        ],
        ["A", "B"],
        default="C",
    )

    return product_summary["product_code"].map(
        ranked.set_index("product_code")["ABC"]
    )


def classify_xyz(mean_events: pd.Series, cv: pd.Series) -> pd.Series:
    """Classify monthly demand variability."""
    result = pd.Series("Z", index=mean_events.index, dtype="string")

    zero_mean = mean_events == 0
    result.loc[zero_mean] = "No demand"

    result.loc[(~zero_mean) & (cv <= XYZ_X_MAX_CV)] = "X"
    result.loc[
        (~zero_mean)
        & (cv > XYZ_X_MAX_CV)
        & (cv <= XYZ_Y_MAX_CV)
    ] = "Y"
    result.loc[(~zero_mean) & (cv > XYZ_Y_MAX_CV)] = "Z"

    return result


def classify_fsn(active_months: pd.Series) -> pd.Series:
    """Classify how frequently products were dispensed."""
    return pd.Series(
        np.select(
            [
                active_months >= FSN_F_MIN_MONTHS,
                active_months >= FSN_S_MIN_MONTHS,
            ],
            ["F", "S"],
            default="N",
        ),
        index=active_months.index,
        dtype="string",
    )


def main() -> None:
    monthly = pd.read_parquet(INPUT_PATH)

    required = {
        "product_code",
        "designation",
        "month",
        "dispensing_events",
    }
    missing = required - set(monthly.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if monthly.duplicated(["product_code", "month"]).any():
        raise ValueError("Duplicate product-month rows found.")

    monthly["dispensing_events"] = pd.to_numeric(
        monthly["dispensing_events"], errors="raise"
    )

    if (monthly["dispensing_events"] < 0).any():
        raise ValueError("Negative dispensing-event counts found.")

    month_count = monthly["month"].nunique()
    if month_count != 11:
        raise ValueError(f"Expected 11 months, found {month_count}.")

    summary = (
        monthly.groupby(["product_code", "designation"], as_index=False)
        .agg(
            total_events=("dispensing_events", "sum"),
            active_months=("dispensing_events", lambda s: (s > 0).sum()),
            mean_monthly_events=("dispensing_events", "mean"),
            std_monthly_events=("dispensing_events", "std"),
        )
    )

    # Use population standard deviation for the 11 observed months.
    population_std = (
        monthly.groupby(["product_code", "designation"])["dispensing_events"]
        .std(ddof=0)
        .rename("std_monthly_events")
        .reset_index()
    )

    summary = summary.drop(columns="std_monthly_events").merge(
        population_std,
        on=["product_code", "designation"],
        validate="one_to_one",
    )

    summary["cv"] = np.where(
        summary["mean_monthly_events"] > 0,
        summary["std_monthly_events"] / summary["mean_monthly_events"],
        np.nan,
    )

    summary["ABC"] = classify_abc(summary)
    summary["XYZ"] = classify_xyz(
        summary["mean_monthly_events"], summary["cv"]
    )
    summary["FSN"] = classify_fsn(summary["active_months"])

    summary["abc_xyz_fsn"] = (
        summary["ABC"] + "-" + summary["XYZ"] + "-" + summary["FSN"]
    )

    summary = summary.sort_values(
        ["ABC", "total_events"], ascending=[True, False]
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary.to_parquet(OUTPUT_PATH, index=False)

    # A simple monthly overview, based only on dispensing events.
    monthly_summary = (
        monthly.groupby("month", as_index=False)
        .agg(
            dispensing_events=("dispensing_events", "sum"),
            products_with_demand=("dispensing_events", lambda s: (s > 0).sum()),
        )
        .sort_values("month")
    )
    monthly_summary.to_csv(
        MONTHLY_SUMMARY_PATH, index=False, encoding="utf-8-sig"
    )

    print("DEMAND CLASSIFICATION")
    print("=" * 45)
    print(f"Products classified: {len(summary):,}")
    print(f"Months analyzed: {month_count}")
    print(f"Total dispensing events: {summary['total_events'].sum():,}")

    for column in ["ABC", "XYZ", "FSN"]:
        print(f"\n{column} distribution:")
        print(summary[column].value_counts(dropna=False).to_string())

    print("\nCombined ABC-XYZ-FSN classes:")
    print(summary["abc_xyz_fsn"].value_counts().to_string())

    print(f"\nClassification output: {OUTPUT_PATH}")
    print(f"Monthly summary: {MONTHLY_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
