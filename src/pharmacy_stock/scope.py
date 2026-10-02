import pandas as pd


def compare_product_scope(
    full_inventory: pd.DataFrame,
    monitored_inventory: pd.DataFrame,
) -> dict:
    """Compare the monitored product population with the full inventory."""

    full_codes = set(
        full_inventory["product_code"]
        .dropna()
        .astype(str)
    )

    monitored_codes = set(
        monitored_inventory["product_code"]
        .dropna()
        .astype(str)
    )

    monitored_found = monitored_codes & full_codes
    monitored_missing = monitored_codes - full_codes
    not_monitored = full_codes - monitored_codes

    total_full = len(full_codes)
    total_monitored = len(monitored_codes)

    product_coverage = (
        len(monitored_found) / total_full * 100
        if total_full
        else 0.0
    )

    return {
        "total_full_products": total_full,
        "total_monitored_products": total_monitored,
        "monitored_products_found": len(monitored_found),
        "monitored_products_missing": len(monitored_missing),
        "products_not_monitored": len(not_monitored),
        "product_coverage_percent": product_coverage,
        "monitored_found_codes": monitored_found,
        "monitored_missing_codes": monitored_missing,
        "not_monitored_codes": not_monitored,
    }


def calculate_financial_coverage(
    full_inventory: pd.DataFrame,
    monitored_codes: set,
) -> dict:
    """Calculate the September financial coverage of monitored products."""

    full_value = float(
        full_inventory["stock_value"].sum()
    )

    monitored_value = float(
        full_inventory[
            full_inventory["product_code"]
            .astype(str)
            .isin(monitored_codes)
        ]["stock_value"].sum()
    )

    financial_coverage = (
        monitored_value / full_value * 100
        if full_value
        else 0.0
    )

    return {
        "full_inventory_value": full_value,
        "monitored_inventory_value": monitored_value,
        "financial_coverage_percent": financial_coverage,
    }
