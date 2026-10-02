# from pathlib import Path

# import pandas as pd

# from pharmacy_stock.scope import (
#     compare_product_scope,
#     calculate_financial_coverage,
# )


# FULL_INVENTORY = Path(
#     "data/processed/full_inventory_2026_09_clean.parquet"
# )

# MONITORED_INVENTORY = Path(
#     "data/processed/inventory_2026_08.parquet"
# )

# OUTPUT_DIR = Path(
#     "data/processed/scope"
# )


# def main():
#     print("Pharmacy monitoring scope analysis")
#     print("==================================")

#     full_inventory = pd.read_parquet(
#         FULL_INVENTORY
#     )

#     monitored_inventory = pd.read_parquet(
#         MONITORED_INVENTORY
#     )

#     scope = compare_product_scope(
#         full_inventory,
#         monitored_inventory,
#     )

#     financial = calculate_financial_coverage(
#         full_inventory,
#         scope["monitored_found_codes"],
#     )

#     print("\nProduct scope")
#     print("-------------")
#     print(
#         f"Full pharmacy products: "
#         f"{scope['total_full_products']}"
#     )
#     print(
#         f"Monitored products: "
#         f"{scope['total_monitored_products']}"
#     )
#     print(
#         f"Monitored products found: "
#         f"{scope['monitored_products_found']}"
#     )
#     print(
#         f"Monitored products missing: "
#         f"{scope['monitored_products_missing']}"
#     )
#     print(
#         f"Products not monitored: "
#         f"{scope['products_not_monitored']}"
#     )
#     print(
#         f"Product coverage: "
#         f"{scope['product_coverage_percent']:.2f}%"
#     )

#     print("\nFinancial scope")
#     print("---------------")
#     print(
#         f"Full September inventory value: "
#         f"€{financial['full_inventory_value']:,.2f}"
#     )
#     print(
#         f"Value of monitored products: "
#         f"€{financial['monitored_inventory_value']:,.2f}"
#     )
#     print(
#         f"Financial coverage: "
#         f"{financial['financial_coverage_percent']:.2f}%"
#     )

#     OUTPUT_DIR.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     # Monitored products not found in full inventory
#     pd.DataFrame(
#         sorted(scope["monitored_missing_codes"]),
#         columns=["product_code"],
#     ).to_csv(
#         OUTPUT_DIR / "monitored_products_missing.csv",
#         index=False,
#     )

#     # Products in pharmacy but not monitored
#     pd.DataFrame(
#         sorted(scope["not_monitored_codes"]),
#         columns=["product_code"],
#     ).to_csv(
#         OUTPUT_DIR / "products_not_monitored.csv",
#         index=False,
#     )

#     print("\nScope files saved to:")
#     print(OUTPUT_DIR)


# if __name__ == "__main__":
#     main()

from pathlib import Path

import pandas as pd

from pharmacy_stock.scope import (
    compare_product_scope,
    calculate_financial_coverage,
)


FULL_INVENTORY = Path(
    "data/processed/full_inventory_2026_09_clean.parquet"
)

MONITORED_INVENTORY = Path(
    "data/processed/inventory_2026_08.parquet"
)

OUTPUT_DIR = Path(
    "data/processed/scope"
)


def main():
    print("Pharmacy monitoring scope analysis")
    print("==================================")

    full_inventory = pd.read_parquet(
        FULL_INVENTORY
    )

    monitored_inventory = pd.read_parquet(
        MONITORED_INVENTORY
    )

    scope = compare_product_scope(
        full_inventory,
        monitored_inventory,
    )

    financial = calculate_financial_coverage(
        full_inventory,
        scope["monitored_found_codes"],
    )

    print("\nProduct scope")
    print("-------------")
    print(
        f"Full pharmacy products: "
        f"{scope['total_full_products']}"
    )
    print(
        f"Monitored products: "
        f"{scope['total_monitored_products']}"
    )
    print(
        f"Monitored products found: "
        f"{scope['monitored_products_found']}"
    )
    print(
        f"Monitored products missing: "
        f"{scope['monitored_products_missing']}"
    )
    print(
        f"Products not monitored: "
        f"{scope['products_not_monitored']}"
    )
    print(
        f"Product coverage: "
        f"{scope['product_coverage_percent']:.2f}%"
    )

    print("\nFinancial scope")
    print("---------------")
    print(
        f"Full September inventory value: "
        f"€{financial['full_inventory_value']:,.2f}"
    )
    print(
        f"Value of monitored products: "
        f"€{financial['monitored_inventory_value']:,.2f}"
    )
    print(
        f"Financial coverage: "
        f"{financial['financial_coverage_percent']:.2f}%"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------
    # Products monitored in August but missing in September
    # --------------------------------------------------

    missing_codes = scope["monitored_missing_codes"]

    missing_monitored_products = (
        monitored_inventory[
            monitored_inventory["product_code"]
            .astype(str)
            .isin(missing_codes)
        ][
            [
                "product_code",
                "designation",
                "stock_after",
                "net_purchase_price",
                "stock_value",
            ]
        ]
        .sort_values("designation")
        .reset_index(drop=True)
    )

    missing_monitored_products.to_csv(
        OUTPUT_DIR / "monitored_products_missing.csv",
        index=False,
    )

    # --------------------------------------------------
    # Products in the pharmacy but not monitored
    # --------------------------------------------------

    pd.DataFrame(
        sorted(scope["not_monitored_codes"]),
        columns=["product_code"],
    ).to_csv(
        OUTPUT_DIR / "products_not_monitored.csv",
        index=False,
    )

    print("\nScope files saved to:")
    print(OUTPUT_DIR)

    print("\nMissing monitored products report")
    print("---------------------------------")
    print(
        f"Products: {len(missing_monitored_products)}"
    )
    print(
        "File: "
        f"{OUTPUT_DIR / 'monitored_products_missing.csv'}"
    )


if __name__ == "__main__":
    main()
