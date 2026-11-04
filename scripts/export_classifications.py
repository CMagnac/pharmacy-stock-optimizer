
from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = ROOT / "data" / "processed"

CLASSIFICATION_FILE = (
    PROCESSED_DIR
    / "demand_classifications_nov2025_sep2026.parquet"
)

ATC_REFERENCE_FILE = PROCESSED_DIR / "atc_reference.parquet"

OUTPUT_FILES = {
    "ABC": PROCESSED_DIR / "ABC_product.csv",
    "XYZ": PROCESSED_DIR / "XYZ_product.csv",
    "FSN": PROCESSED_DIR / "FSN_product.csv",
}

UNMATCHED_FILE = PROCESSED_DIR / "products_without_atc.csv"

ENRICHED_FILE = (
    PROCESSED_DIR
    / "demand_classifications_with_atc.parquet"
)


# ============================================================
# VALIDATION
# ============================================================

REQUIRED_CLASSIFICATION_COLUMNS = {
    "product_code",
    "designation",
    "ABC",
    "XYZ",
    "FSN",
}

REQUIRED_ATC_COLUMNS = {
    "cip13",
    "atc_code",
}

ATC5_PATTERN = r"[A-Z]\d{2}[A-Z]{2}\d{2}"


def validate_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
    dataframe_name: str,
) -> None:

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            f"{dataframe_name} is missing columns: "
            f"{sorted(missing_columns)}"
        )


def main():

    # ========================================================
    # 1. LOAD DATA
    # ========================================================

    print("Loading classification and ATC reference data...")

    if not CLASSIFICATION_FILE.exists():
        raise FileNotFoundError(CLASSIFICATION_FILE)

    if not ATC_REFERENCE_FILE.exists():
        raise FileNotFoundError(ATC_REFERENCE_FILE)

    classifications = pd.read_parquet(CLASSIFICATION_FILE)
    atc_reference = pd.read_parquet(ATC_REFERENCE_FILE)

    validate_columns(
        classifications,
        REQUIRED_CLASSIFICATION_COLUMNS,
        "Classification dataset",
    )

    validate_columns(
        atc_reference,
        REQUIRED_ATC_COLUMNS,
        "ATC reference",
    )

    print(f"Monitored products: {len(classifications):,}")
    print(f"ATC reference rows: {len(atc_reference):,}")

    # ========================================================
    # 2. NORMALIZE IDENTIFIERS AND ATC CODES
    # ========================================================

    classifications["product_code"] = (
        classifications["product_code"]
        .astype("string")
        .str.strip()
    )

    atc_reference["cip13"] = (
        atc_reference["cip13"]
        .astype("string")
        .str.strip()
    )

    atc_reference["atc_code"] = (
        atc_reference["atc_code"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # Validate CIP13 format.
    invalid_product_codes = ~classifications[
        "product_code"
    ].str.fullmatch(r"\d{13}", na=False)

    invalid_reference_codes = ~atc_reference[
        "cip13"
    ].str.fullmatch(r"\d{13}", na=False)

    if invalid_product_codes.any():
        raise ValueError(
            f"{invalid_product_codes.sum()} monitored products "
            "have invalid CIP13 identifiers."
        )

    if invalid_reference_codes.any():
        raise ValueError(
            f"{invalid_reference_codes.sum()} ATC reference rows "
            "have invalid CIP13 identifiers."
        )

    # Validate ATC5 format.
    invalid_atc_codes = ~atc_reference[
        "atc_code"
    ].str.fullmatch(ATC5_PATTERN, na=False)

    if invalid_atc_codes.any():
        raise ValueError(
            f"{invalid_atc_codes.sum()} ATC reference rows "
            "do not contain valid ATC5 codes."
        )

    # ========================================================
    # 3. CHECK DUPLICATE AND CONFLICTING MAPPINGS
    # ========================================================

    conflicts = (
        atc_reference.groupby("cip13")["atc_code"]
        .nunique()
    )

    conflicts = conflicts[conflicts > 1]

    if not conflicts.empty:
        raise ValueError(
            f"{len(conflicts)} CIP13 identifiers have "
            "conflicting ATC5 codes."
        )

    # Remove exact duplicate mappings.
    atc_reference = atc_reference.drop_duplicates(
        subset=["cip13", "atc_code"]
    )

    # Ensure one row per CIP13 before merging.
    if atc_reference["cip13"].duplicated().any():
        raise ValueError(
            "The ATC reference contains duplicate CIP13 identifiers."
        )

    # ========================================================
    # 4. JOIN CLASSIFICATIONS WITH ATC REFERENCE
    # ========================================================

    enriched = classifications.merge(
        atc_reference[["cip13", "atc_code"]],
        left_on="product_code",
        right_on="cip13",
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    # Preserve unmatched products with an empty ATC code.
    enriched["atc_code"] = enriched["atc_code"].fillna("")

    matched = enriched["_merge"].eq("both")
    unmatched = ~matched

    # ========================================================
    # 5. DISPLAY MATCHING RESULTS
    # ========================================================

    total_products = len(enriched)
    matched_count = int(matched.sum())
    unmatched_count = int(unmatched.sum())

    matching_rate = (
        matched_count / total_products
        if total_products
        else 0
    )

    print("\nATC MATCHING RESULTS")
    print("=" * 45)

    print(f"Total monitored products: {total_products:,}")
    print(f"Products matched:         {matched_count:,}")
    print(f"Products unmatched:       {unmatched_count:,}")
    print(f"Matching rate:            {matching_rate:.2%}")

    # ========================================================
    # 6. EXPORT UNMATCHED PRODUCTS
    # ========================================================

    unmatched_products = enriched.loc[
        unmatched,
        ["product_code", "designation"],
    ].copy()

    unmatched_products.to_csv(
        UNMATCHED_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"\nUnmatched products exported: {UNMATCHED_FILE.name}")

    # ========================================================
    # 7. EXPORT ENRICHED CLASSIFICATION DATASET
    # ========================================================

    enriched = enriched.drop(
        columns=["cip13", "_merge"]
    )

    enriched.to_parquet(
        ENRICHED_FILE,
        index=False,
    )

    print(f"Enriched dataset exported: {ENRICHED_FILE.name}")

    # ========================================================
    # 8. EXPORT ABC, XYZ AND FSN CSV FILES
    # ========================================================

    for classification, output_file in OUTPUT_FILES.items():

        export = enriched[
            [
                "product_code",
                "designation",
                classification,
                "atc_code",
            ]
        ].copy()

        export = export.rename(
            columns={
                classification: "class",
                "atc_code": "ATC_code",
            }
        )

        export.to_csv(
            output_file,
            index=False,
            encoding="utf-8-sig",
        )

        print(
            f"{classification} exported: "
            f"{output_file.name} ({len(export):,} rows)"
        )

    # ========================================================
    # 9. FINAL VALIDATION
    # ========================================================

    print("\nFINAL VALIDATION")
    print("=" * 45)

    for classification, output_file in OUTPUT_FILES.items():

        exported = pd.read_csv(
            output_file,
            dtype={"product_code": "string", "ATC_code": "string"},
        )

        print(
            f"{output_file.name}: "
            f"{len(exported):,} rows | "
            f"{exported['product_code'].nunique():,} unique products"
        )

        if len(exported) != total_products:
            raise ValueError(
                f"{output_file.name} does not contain "
                "the expected number of products."
            )

        if exported["product_code"].duplicated().any():
            raise ValueError(
                f"{output_file.name} contains duplicate product codes."
            )

    print("\nAll classification files successfully exported.")


if __name__ == "__main__":
    main()
