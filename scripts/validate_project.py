"""Project-level validation. Run: python scripts/validate_project.py"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import pandas as pd

EXPECTED_MONTHS = 11
START = pd.Timestamp("2025-11-01")
END = pd.Timestamp("2026-10-01")  # exclusive
DOMAINS = {"ABC": {"A", "B", "C"},
           "XYZ": {"X", "Y", "Z", "No demand"},
           "FSN": {"F", "S", "N"}}

@dataclass
class Check:
    name: str
    status: str
    details: str

class Report:
    def __init__(self):
        self.checks = []
    def add(self, name, ok, details):
        self.checks.append(Check(name, "PASS" if ok else "FAIL", details))
    def info(self, name, details):
        self.checks.append(Check(name, "INFO", details))
    @property
    def failures(self):
        return sum(c.status == "FAIL" for c in self.checks)
    def display(self):
        print("\n" + "=" * 72)
        print("PHARMACY STOCK OPTIMIZATION — PROJECT VALIDATION")
        print("=" * 72)
        for c in self.checks:
            print(f"[{c.status:4}] {c.name}: {c.details}")
        print("-" * 72)
        print(f"Failures: {self.failures}")
        print("OVERALL:", "FAILED" if self.failures else "PASSED")

def normalize_codes(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)

def duplicate_values(values: pd.Series) -> list[str]:
    s = normalize_codes(values)
    return [str(x) for x in s[s.duplicated(keep=False)].dropna().unique()[:10]]

def validate_classification(frame: pd.DataFrame, class_column: str,
                            allowed_values: set[str]) -> tuple[bool, str]:
    missing = {"product_code", class_column} - set(frame.columns)
    if missing:
        return False, f"Missing columns: {sorted(missing)}"
    codes = normalize_codes(frame["product_code"])
    if codes.isna().any() or codes.eq("").any():
        return False, "Missing product_code values."
    duplicates = duplicate_values(codes)
    if duplicates:
        return False, f"Duplicate product codes: {duplicates}"
    values = frame[class_column].astype("string").str.strip()
    if values.isna().any() or values.eq("").any():
        return False, "Missing class values."
    unexpected = sorted(set(values.unique()) - allowed_values)
    if unexpected:
        return False, f"Unexpected class values: {unexpected}"
    return True, f"{len(frame)} unique products; values={sorted(values.unique())}"

def validate_event_reconciliation(event_demand: pd.DataFrame,
                                  billing: pd.DataFrame,
                                  monitored_codes: Iterable[str]) -> tuple[bool, str]:
    d_required = {"product_code", "month", "dispensing_events", "boxes_dispensed"}
    b_required = {"product_code", "transaction_date", "quantity_dispensed"}
    md, mb = d_required - set(event_demand), b_required - set(billing)
    if md or mb:
        return False, f"Missing demand columns={sorted(md)}; billing columns={sorted(mb)}"
    demand, tx = event_demand.copy(), billing.copy()
    demand["product_code"] = normalize_codes(demand.product_code)
    tx["product_code"] = normalize_codes(tx.product_code)
    monitored = set(normalize_codes(pd.Series(list(monitored_codes))).dropna())
    demand = demand[demand.product_code.isin(monitored)]
    tx["transaction_date"] = pd.to_datetime(tx.transaction_date, errors="coerce")
    tx["quantity_dispensed"] = pd.to_numeric(tx.quantity_dispensed, errors="coerce")
    tx = tx[tx.product_code.isin(monitored)
            & tx.transaction_date.ge(START) & tx.transaction_date.lt(END)
            & tx.quantity_dispensed.gt(0)]
    events = int(pd.to_numeric(demand.dispensing_events, errors="coerce").fillna(0).sum())
    billing_events = len(tx)
    boxes = float(pd.to_numeric(demand.boxes_dispensed, errors="coerce").fillna(0).sum())
    billing_boxes = float(tx.quantity_dispensed.sum())
    ok = events == billing_events and abs(boxes - billing_boxes) < 1e-9
    return ok, (f"Events: demand={events:,}, billing records={billing_events:,}; "
                f"boxes: demand={boxes:,.0f}, billing={billing_boxes:,.0f}")

def run_validation(root: Path, expected_products: int = 699) -> Report:
    report, data = Report(), root / "data" / "processed"
    required_files = [
        "monitored_product_registry.csv", "billing_history_clean.parquet",
        "monthly_event_demand_nov2025_sep2026.parquet",
        "demand_classifications_with_atc.parquet",
        "ABC_product.csv", "XYZ_product.csv", "FSN_product.csv",
        "monitored_inventory_history.parquet",
    ]
    for name in required_files:
        found = (data / name).is_file()
        report.add(f"File: {name}", found, "Found" if found else f"Missing: {data / name}")

    registry_path = data / "monitored_product_registry.csv"
    billing_path = data / "billing_history_clean.parquet"
    demand_path = data / "monthly_event_demand_nov2025_sep2026.parquet"
    codes = []
    if registry_path.exists():
        try:
            registry = pd.read_csv(registry_path, dtype={"product_code": "string"})
            if "product_code" not in registry:
                report.add("Registry schema", False, "No product_code column")
            else:
                s = normalize_codes(registry.product_code)
                dup = duplicate_values(s)
                ok = len(registry) == expected_products and s.notna().all() and s.ne("").all() and not dup
                report.add("Monitored registry", ok,
                           f"rows={len(registry)}, unique={s.nunique()}, expected={expected_products}, duplicates={dup}")
                codes = s.dropna().tolist()
        except Exception as exc:
            report.add("Registry readable", False, str(exc))

    demand = None
    if demand_path.exists():
        try:
            demand = pd.read_parquet(demand_path)
            needed = {"product_code", "month", "dispensing_events", "boxes_dispensed"}
            missing = needed - set(demand.columns)
            if missing:
                report.add("Demand schema", False, f"Missing columns: {sorted(missing)}")
            else:
                months = pd.to_datetime(demand.month, errors="coerce").dt.to_period("M")
                duplicate_keys = demand.assign(_month=months).duplicated(["product_code", "_month"]).sum()
                expected_rows = expected_products * EXPECTED_MONTHS
                ok = len(demand) == expected_rows and months.nunique() == EXPECTED_MONTHS and duplicate_keys == 0
                report.add("Monthly event-demand grid", ok,
                           f"rows={len(demand)}/{expected_rows}; months={months.nunique()}/{EXPECTED_MONTHS}; duplicate product-months={duplicate_keys}")
                numeric = demand[["dispensing_events", "boxes_dispensed"]].apply(pd.to_numeric, errors="coerce")
                report.add("Non-negative demand", not numeric.lt(0).any().any(),
                           "No negative counts" if not numeric.lt(0).any().any() else "Negative counts found")
        except Exception as exc:
            report.add("Demand readable", False, str(exc))

    if billing_path.exists():
        try:
            billing = pd.read_parquet(billing_path)
            required = {"product_code", "transaction_date", "quantity_dispensed"}
            missing = required - set(billing.columns)
            report.add("Billing schema", not missing,
                       f"Missing columns: {sorted(missing)}" if missing else f"{len(billing):,} rows")
            if demand is not None and not missing and codes:
                ok, details = validate_event_reconciliation(demand, billing, codes)
                report.add("Dispensing-event reconciliation", ok, details)
        except Exception as exc:
            report.add("Billing readable", False, str(exc))

    class_sets = {}
    for kind, allowed in DOMAINS.items():
        path = data / f"{kind}_product.csv"
        if not path.exists():
            continue
        try:
            frame = pd.read_csv(path, dtype={"product_code": "string"})
            ok, details = validate_classification(frame, "class", allowed)
            report.add(f"{kind} classification", ok, details)
            if ok:
                class_sets[kind] = set(normalize_codes(frame.product_code).dropna())
        except Exception as exc:
            report.add(f"{kind} classification readable", False, str(exc))
    if len(class_sets) == 3:
        same = class_sets["ABC"] == class_sets["XYZ"] == class_sets["FSN"]
        report.add("Classification product-set consistency", same,
                   "All three exports contain the same product set" if same else "Product sets differ")
        if codes:
            report.add("Classification registry coverage", class_sets["ABC"] == set(codes),
                       f"classified={len(class_sets['ABC'])}; registry={len(set(codes))}")

    enriched_path = data / "demand_classifications_with_atc.parquet"
    if enriched_path.exists():
        try:
            enriched = pd.read_parquet(enriched_path)
            col = next((c for c in ("ATC_code", "atc_code", "atc5") if c in enriched), None)
            if col:
                mapped = int(enriched[col].notna().sum())
                report.info("ATC5 reference coverage",
                            f"{mapped}/{len(enriched)} mapped ({mapped / max(len(enriched), 1) * 100:.2f}%). "
                            "Informational only: MITM is not a comprehensive ATC5 reference.")
        except Exception as exc:
            report.info("ATC5 reference coverage", f"Could not inspect: {exc}")

    history_path = data / "monitored_inventory_history.parquet"
    if history_path.exists():
        try:
            history = pd.read_parquet(history_path)
            status = next((c for c in ("observation_status", "status") if c in history), None)
            if status:
                values = set(history[status].dropna().astype(str).str.lower())
                explicit_missing = any("missing" in x for x in values)
                report.add("Missing inventory observations", explicit_missing,
                           f"status values={sorted(values)}; missing must not be interpreted as zero stock")
            else:
                report.info("Inventory observation status", "No status column found; review schema manually")
            report.info("Inventory history dimensions", f"{len(history):,} rows")
        except Exception as exc:
            report.add("Inventory history readable", False, str(exc))

    figures = root / "reports" / "figures"
    expected_figures = ["classification_distributions.png", "abc_xyz_heatmap.png",
                        "combined_classifications.png", "atc5_coverage.png", "top_atc5_codes.png"]
    found = [f for f in expected_figures if (figures / f).is_file()]
    report.info("Classification figures", f"{len(found)}/{len(expected_figures)} present: {found}")
    return report

def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Validate processed project outputs.")
    parser.add_argument("--root", type=Path, default=project_root)
    parser.add_argument("--expected-products", type=int, default=699)
    args = parser.parse_args()
    result = run_validation(args.root.resolve(), args.expected_products)
    result.display()
    return 1 if result.failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
