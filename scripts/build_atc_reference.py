
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

CIP_FILE = RAW_DIR / "CIS_CIP_bdpm.txt"
MITM_FILE = RAW_DIR / "CIS_MITM.txt"

OUTPUT_FILE = PROCESSED_DIR / "atc_reference.parquet"

CIP_COLUMNS = [
    "CIS",
    "CIP7",
    "presentation",
    "presentation_status",
    "commercialization_status",
    "commercialization_date",
    "CIP13",
    "community_approval",
    "reimbursement_rate",
    "price",
    "public_price",
    "reimbursement_tariff",
    "reimbursement_conditions",
]

MITM_COLUMNS = [
    "CIS",
    "ATC",
    "medicine_name",
    "holder",
    "operator",
    "authorization_date",
    "medicine_url",
]

ATC5_PATTERN = r"[A-Z]\d{2}[A-Z]{2}\d{2}"


def read_official_file(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

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
            f"Unexpected number of columns in {path.name}: "
            f"expected {len(columns)}, found {df.shape[1]}."
        )

    df.columns = columns

    for column in df.columns:
        df[column] = df[column].str.strip()

    return df


def main():
    print("Reading official BDPM files...")

    cip = read_official_file(CIP_FILE, CIP_COLUMNS)
    mitm = read_official_file(MITM_FILE, MITM_COLUMNS)

    # Normalize identifiers and ATC codes.
    cip["CIS"] = cip["CIS"].str.strip()
    cip["CIP7"] = cip["CIP7"].str.strip()
    cip["CIP13"] = cip["CIP13"].str.strip()

    mitm["CIS"] = mitm["CIS"].str.strip()
    mitm["ATC"] = mitm["ATC"].str.strip().str.upper()

    # Keep only valid ATC5 codes.
    atc5 = mitm[
        mitm["ATC"].str.fullmatch(ATC5_PATTERN, na=False)
    ].copy()

    print(f"CIP presentations: {len(cip):,}")
    print(f"Medicine records: {len(mitm):,}")
    print(f"ATC5 records: {len(atc5):,}")

    # Keep the CIS-to-ATC5 relationship.
    atc_mapping = atc5[["CIS", "ATC"]].drop_duplicates()

    # Check whether a CIS has multiple ATC5 codes.
    conflicts = (
        atc_mapping.groupby("CIS")["ATC"]
        .nunique()
    )

    conflicts = conflicts[conflicts > 1]

    if not conflicts.empty:
        raise ValueError(
            f"{len(conflicts)} CIS identifiers have multiple ATC5 codes. "
            "Inspect these records before proceeding."
        )

    # Join CIP presentations to their ATC5 codes.
    reference = cip.merge(
        atc_mapping,
        on="CIS",
        how="inner",
        validate="many_to_one",
    )

    reference = reference.rename(columns={"ATC": "ATC_code"})

    # Keep valid identifiers.
    reference = reference[
        reference["CIP13"].str.fullmatch(r"\d{13}", na=False)
        & reference["CIP7"].str.fullmatch(r"\d{7}", na=False)
    ].copy()

    reference = reference[
        ["CIS", "CIP7", "CIP13", "ATC_code", "presentation"]
    ].drop_duplicates()

    # Check whether one CIP13 has conflicting ATC5 codes.
    conflicts = (
        reference.groupby("CIP13")["ATC_code"]
        .nunique()
    )
    conflicts = conflicts[conflicts > 1]

    if not conflicts.empty:
        raise ValueError(
            f"{len(conflicts)} CIP13 identifiers have conflicting ATC5 codes."
        )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    reference.to_parquet(OUTPUT_FILE, index=False)

    print("\nATC reference successfully generated.")
    print(f"Unique CIP13: {reference['CIP13'].nunique():,}")
    print(f"Unique CIS: {reference['CIS'].nunique():,}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
