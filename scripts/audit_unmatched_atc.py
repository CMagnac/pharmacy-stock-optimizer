"""
Audit monitored products that could not be enriched with an ATC5 code.

Inputs
------
data/processed/products_without_atc.csv
data/raw/CIS_CIP_bdpm.txt
data/raw/CIS_MITM.txt

Output
------
reports/analysis/unmatched_atc_audit.csv

The script distinguishes:
- CIP13_NOT_FOUND: product CIP13 is absent from the official CIP presentation file.
- CIS_NOT_FOUND_IN_MITM: CIP13 exists, but its CIS has no record in the MITM file.
- CIS_HAS_NON_ATC5_ONLY: CIS exists in MITM, but no valid seven-character ATC5 code is present.
- ATC5_AVAILABLE_BUT_NOT_MAPPED: an ATC5 code is present for the CIS; investigate the existing reference/join.
- MULTIPLE_CIS_OR_ATC5: the source data provides multiple candidate identifiers/codes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNMATCHED_FILE = PROJECT_ROOT / "data" / "processed" / "products_without_atc.csv"
CIP_FILE = PROJECT_ROOT / "data" / "raw" / "CIS_CIP_bdpm.txt"
MITM_FILE = PROJECT_ROOT / "data" / "raw" / "CIS_MITM.txt"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "analysis"
OUTPUT_FILE = OUTPUT_DIR / "unmatched_atc_audit.csv"

CIP_COLUMNS = [
    "cis",
    "cip7",
    "presentation",
    "presentation_status",
    "commercialization_status",
    "commercialization_date",
    "cip13",
    "community_approval",
    "reimbursement_rate",
    "price",
    "public_price",
    "reimbursement_tariff",
    "reimbursement_conditions",
]

MITM_COLUMNS = [
    "cis",
    "atc_code",
    "medicine_name",
    "holder",
    "operator",
    "authorization_date",
    "medicine_url",
]

ATC5_PATTERN = r"^[A-Z]\d{2}[A-Z]{2}\d{2}$"


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    sys.exit(1)


def find_column(df: pd.DataFrame, candidates: list[str], description: str) -> str:
    """Find a column without depending on capitalization or surrounding spaces."""
    normalized = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    fail(
        f"Could not identify the {description} column in "
        f"{list(df.columns)}. Expected one of: {candidates}"
    )
    raise AssertionError("Unreachable")


def normalize_digits(value: object) -> str:
    if pd.isna(value):
        return ""
    return "".join(char for char in str(value).strip() if char.isdigit())


def load_source_file(path: Path, columns: list[str], label: str) -> pd.DataFrame:
    if not path.exists():
        fail(f"{label} file not found: {path}")

    try:
        df = pd.read_csv(
            path,
            sep="\t",
            header=None,
            names=columns,
            dtype=str,
            encoding="cp1252",
            keep_default_na=False,
            on_bad_lines="error",
        )
    except Exception as exc:
        fail(f"Unable to read {label} file {path}: {exc}")

    # Remove a possible UTF-8/Unicode BOM from the first field.
    df.columns = [str(col).replace("\ufeff", "").strip().lower() for col in df.columns]
    for column in df.columns:
        df[column] = df[column].astype(str).str.strip()

    return df


def main() -> None:
    print("Loading unmatched products and official BDPM reference files...")

    if not UNMATCHED_FILE.exists():
        fail(f"Unmatched-products file not found: {UNMATCHED_FILE}")

    try:
        unmatched = pd.read_csv(
            UNMATCHED_FILE,
            dtype=str,
            encoding="utf-8-sig",
            keep_default_na=False,
        )
    except Exception as exc:
        fail(f"Unable to read {UNMATCHED_FILE}: {exc}")

    product_col = find_column(
        unmatched,
        ["product_code", "cip13", "code_cip13", "cip"],
        "product CIP13",
    )
    designation_col = next(
        (
            col for col in unmatched.columns
            if str(col).strip().lower() in {"designation", "product_name", "name", "libelle"}
        ),
        None,
    )

    unmatched["product_code_normalized"] = unmatched[product_col].map(normalize_digits)
    if designation_col is None:
        unmatched["designation_for_audit"] = ""
        designation_col = "designation_for_audit"

    invalid_codes = unmatched["product_code_normalized"].str.len().ne(13)
    if invalid_codes.any():
        examples = unmatched.loc[invalid_codes, product_col].head(10).tolist()
        fail(
            "Some unmatched product codes are not 13-digit CIP13 identifiers. "
            f"Examples: {examples}"
        )

    if unmatched["product_code_normalized"].duplicated().any():
        duplicates = unmatched.loc[
            unmatched["product_code_normalized"].duplicated(keep=False),
            "product_code_normalized",
        ].unique().tolist()
        fail(f"Duplicate CIP13 identifiers in unmatched file: {duplicates[:10]}")

    cip = load_source_file(CIP_FILE, CIP_COLUMNS, "CIS_CIP_bdpm")
    mitm = load_source_file(MITM_FILE, MITM_COLUMNS, "CIS_MITM")

    cip["cis_normalized"] = cip["cis"].map(normalize_digits)
    cip["cip13_normalized"] = cip["cip13"].map(normalize_digits)
    mitm["cis_normalized"] = mitm["cis"].map(normalize_digits)
    mitm["atc_code_normalized"] = mitm["atc_code"].str.upper().str.strip()

    cip = cip[
        cip["cip13_normalized"].str.len().eq(13)
        & cip["cis_normalized"].str.len().eq(8)
    ].copy()
    mitm = mitm[mitm["cis_normalized"].str.len().eq(8)].copy()

    # Group source rows by identifiers so that multiple mappings remain visible.
    cip_groups = {
        code: group
        for code, group in cip.groupby("cip13_normalized", sort=False)
    }
    mitm_groups = {
        cis: group
        for cis, group in mitm.groupby("cis_normalized", sort=False)
    }

    audit_rows: list[dict[str, str]] = []

    for _, product in unmatched.iterrows():
        cip13 = product["product_code_normalized"]
        cip_matches = cip_groups.get(cip13)

        base = {
            "product_code": cip13,
            "designation": str(product[designation_col]).strip(),
        }

        if cip_matches is None or cip_matches.empty:
            audit_rows.append(
                {
                    **base,
                    "cis": "",
                    "bdpm_audit_status": "CIP13_NOT_FOUND",
                    "available_atc_codes": "",
                    "available_atc5_codes": "",
                    "cip_source_rows": "0",
                    "cis_candidates": "",
                    "audit_comment": "CIP13 identifier not found in CIS_CIP_bdpm.txt.",
                }
            )
            continue

        cis_values = sorted(set(cip_matches["cis_normalized"]) - {""})
        atc_values: set[str] = set()
        atc5_values: set[str] = set()
        cis_without_mitm: list[str] = []

        for cis in cis_values:
            mitm_matches = mitm_groups.get(cis)
            if mitm_matches is None or mitm_matches.empty:
                cis_without_mitm.append(cis)
                continue

            codes = {
                code for code in mitm_matches["atc_code_normalized"].tolist()
                if code
            }
            atc_values.update(codes)
            atc5_values.update(
                code for code in codes
                if pd.Series([code]).str.fullmatch(ATC5_PATTERN).iloc[0]
            )

        if len(cis_values) > 1 or len(atc5_values) > 1:
            status = "MULTIPLE_CIS_OR_ATC5"
            comment = "Multiple CIS identifiers or ATC5 candidates require manual review."
        elif atc5_values:
            status = "ATC5_AVAILABLE_BUT_NOT_MAPPED"
            comment = (
                "An ATC5 code exists for the associated CIS. "
                "Check the reference-generation and join logic."
            )
        elif not cis_values or len(cis_without_mitm) == len(cis_values):
            status = "CIS_NOT_FOUND_IN_MITM"
            comment = "CIP13 exists in the CIP file, but no corresponding CIS record was found in MITM."
        else:
            status = "CIS_HAS_NON_ATC5_ONLY"
            comment = (
                "CIS record exists in MITM, but no code matches the ATC5 format. "
                "Review the source ATC values; do not assume they are all valid lower-level codes."
            )

        audit_rows.append(
            {
                **base,
                "cis": ";".join(cis_values),
                "bdpm_audit_status": status,
                "available_atc_codes": ";".join(sorted(atc_values)),
                "available_atc5_codes": ";".join(sorted(atc5_values)),
                "cip_source_rows": str(len(cip_matches)),
                "cis_candidates": ";".join(cis_without_mitm),
                "audit_comment": comment,
            }
        )

    audit = pd.DataFrame(audit_rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audit.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\nUNMATCHED ATC AUDIT")
    print("=" * 55)
    print(f"Unmatched products audited: {len(audit)}")
    print(f"Unique product codes: {audit['product_code'].nunique()}")
    print("\nAudit status counts:")
    print(audit["bdpm_audit_status"].value_counts(dropna=False).to_string())
    print(f"\nOutput: {OUTPUT_FILE}")

    if len(audit) != len(unmatched):
        fail("Audit output row count does not match the unmatched-products input.")

    print("\nAudit completed successfully. Review the CSV before changing the ATC pipeline.")


if __name__ == "__main__":
    main()
