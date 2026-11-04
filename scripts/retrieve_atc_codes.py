
from pathlib import Path

import pandas as pd


# ============================================================
# 1. PATHS AND CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

CIP_FILE = RAW_DIR / "CIS_CIP_bdpm.txt"
MITM_FILE = RAW_DIR / "CIS_MITM.txt"

OUTPUT_FILE = PROCESSED_DIR / "atc_reference.parquet"

# Official BDPM file column definitions.
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

# ATC5: 7 characters.
ATC5_PATTERN = r"[A-Z]\d{2}[A-Z]{2}\d{2}"


# ============================================================
# 2. READ OFFICIAL BDPM FILES
# ============================================================

def read_bdpm_file(path: Path, columns: list[str]) -> pd.DataFrame:

    if not path.exists():
        raise FileNotFoundError(
            f"Official BDPM file not found: {path}"
        )

    df = pd.read_csv(
        path,
        sep="\t",
        header=None,
        dtype="string",
        encoding="cp1252",
        keep_default_na=False,
        na_filter=False,
        on_bad_lines="error",
    )

    if df.shape[1] != len(columns):
        raise ValueError(
            f"Unexpected structure in {path.name}.\n"
            f"Expected columns: {len(columns)}\n"
            f"Found columns: {df.shape[1]}\n"
            "Check the official BDPM file format before proceeding."
        )

    df.columns = columns

    # Normalize text fields.
    for column in df.columns:
        df[column] = df[column].str.strip()

    return df


# ============================================================
# 3. VALIDATE IDENTIFIERS
# ============================================================

def validate_identifiers(
    cip: pd.DataFrame,
    mitm: pd.DataFrame,
) -> None:

    invalid_cis_cip = ~cip["cis"].str.fullmatch(r"\d{8}", na=False)
    invalid_cis_mitm = ~mitm["cis"].str.fullmatch(r"\d{8}", na=False)

    invalid_cip13 = ~cip["cip13"].str.fullmatch(r"\d{13}", na=False)

    print("\nIDENTIFIER VALIDATION")
    print("=" * 45)

    print(f"Invalid CIS in CIP file: {invalid_cis_cip.sum():,}")
    print(f"Invalid CIS in MITM file: {invalid_cis_mitm.sum():,}")
    print(f"Invalid CIP13 identifiers: {invalid_cip13.sum():,}")

    if invalid_cis_cip.any() or invalid_cis_mitm.any():
        raise ValueError(
            "Invalid CIS identifiers detected. "
            "Inspect the source files before proceeding."
        )

    if invalid_cip13.any():
        raise ValueError(
            "Invalid CIP13 identifiers detected. "
            "Inspect the source file before proceeding."
        )


# ============================================================
# 4. BUILD CIS -> ATC5 MAPPING
# ============================================================

def build_atc_mapping(mitm: pd.DataFrame) -> pd.DataFrame:

    print("\nPROCESSING ATC CODES")
    print("=" * 45)

    # Normalize ATC codes.
    mitm = mitm.copy()

    mitm["atc_code"] = (
        mitm["atc_code"]
        .str.strip()
        .str.upper()
    )

    valid_atc5 = mitm["atc_code"].str.fullmatch(
        ATC5_PATTERN,
        na=False,
    )

    atc5 = mitm.loc[
        valid_atc5,
        ["cis", "atc_code"],
    ].copy()

    print(f"Total MITM records: {len(mitm):,}")
    print(f"Valid ATC5 records: {len(atc5):,}")
    print(f"Excluded non-ATC5 records: {(~valid_atc5).sum():,}")

    # Remove exact duplicate mappings.
    atc5 = atc5.drop_duplicates()

    # Check whether one CIS has multiple ATC5 codes.
    conflicts = (
        atc5.groupby("cis")["atc_code"]
        .nunique()
    )

    conflicts = conflicts[conflicts > 1]

    if not conflicts.empty:

        conflict_file = PROCESSED_DIR / "atc_cis_conflicts.csv"

        conflict_details = (
            atc5[atc5["cis"].isin(conflicts.index)]
            .sort_values(["cis", "atc_code"])
        )

        conflict_details.to_csv(
            conflict_file,
            index=False,
            encoding="utf-8-sig",
        )

        raise ValueError(
            f"{len(conflicts)} CIS identifiers have multiple ATC5 codes.\n"
            f"Conflict details exported to: {conflict_file}"
        )

    # One ATC5 code per CIS.
    atc_mapping = atc5.drop_duplicates(subset="cis")

    print(f"Unique CIS with ATC5: {atc_mapping['cis'].nunique():,}")

    return atc_mapping


# ============================================================
# 5. JOIN CIP13 -> CIS -> ATC5
# ============================================================

def build_cip_atc_reference(
    cip: pd.DataFrame,
    atc_mapping: pd.DataFrame,
) -> pd.DataFrame:

    print("\nJOINING CIP13 TO ATC5")
    print("=" * 45)

    # Keep valid CIP presentations.
    cip_valid = cip[
        cip["cip13"].str.fullmatch(r"\d{13}", na=False)
    ].copy()

    # Keep only necessary columns.
    cip_valid = cip_valid[
        ["cis", "cip7", "cip13", "presentation"]
    ].drop_duplicates()

    # Join through CIS.
    reference = cip_valid.merge(
        atc_mapping,
        on="cis",
        how="inner",
        validate="many_to_one",
    )

    # Check whether one CIP13 has multiple ATC5 codes.
    conflicts = (
        reference.groupby("cip13")["atc_code"]
        .nunique()
    )

    conflicts = conflicts[conflicts > 1]

    if not conflicts.empty:

        conflict_file = PROCESSED_DIR / "atc_cip13_conflicts.csv"

        conflict_details = (
            reference[reference["cip13"].isin(conflicts.index)]
            .sort_values(["cip13", "atc_code"])
        )

        conflict_details.to_csv(
            conflict_file,
            index=False,
            encoding="utf-8-sig",
        )

        raise ValueError(
            f"{len(conflicts)} CIP13 identifiers have multiple ATC5 codes.\n"
            f"Conflict details exported to: {conflict_file}"
        )

    # Remove exact duplicate rows.
    reference = reference.drop_duplicates(
        subset=["cis", "cip13", "atc_code"]
    )

    return reference


# ============================================================
# 6. MAIN
# ============================================================

def main():

    print("Reading official BDPM files...")

    cip = read_bdpm_file(
        CIP_FILE,
        CIP_COLUMNS,
    )

    mitm = read_bdpm_file(
        MITM_FILE,
        MITM_COLUMNS,
    )

    print(f"CIP presentations loaded: {len(cip):,}")
    print(f"MITM records loaded: {len(mitm):,}")

    # Validate identifiers.
    validate_identifiers(cip, mitm)

    # Build CIS -> ATC5 mapping.
    atc_mapping = build_atc_mapping(mitm)

    # Build CIP13 -> ATC5 reference.
    reference = build_cip_atc_reference(
        cip,
        atc_mapping,
    )

    # Final column selection and standardization.
    reference = reference[
        ["cis", "cip13", "atc_code"]
    ].drop_duplicates()

    # Check one row per CIP13.
    if reference["cip13"].duplicated().any():
        raise ValueError(
            "Duplicate CIP13 identifiers remain in the final reference."
        )

    # Save reference.
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    reference.to_parquet(
        OUTPUT_FILE,
        index=False,
    )

    # ========================================================
    # 7. FINAL REPORT
    # ========================================================

    print("\nATC REFERENCE SUCCESSFULLY GENERATED")
    print("=" * 45)

    print(f"CIP presentations in source: {len(cip):,}")
    print(f"MITM records in source: {len(mitm):,}")
    print(f"CIP13 mapped to ATC5: {len(reference):,}")
    print(f"Unique CIS: {reference['cis'].nunique():,}")
    print(f"Unique CIP13: {reference['cip13'].nunique():,}")
    print(f"Unique ATC5: {reference['atc_code'].nunique():,}")

    print(f"\nOutput file: {OUTPUT_FILE}")

    print("\nATC5 distribution (top 10):")

    print(
        reference["atc_code"]
        .value_counts()
        .head(10)
        .to_string()
    )


if __name__ == "__main__":
    main()
