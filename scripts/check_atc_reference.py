import pandas as pd

df = pd.read_parquet(
    "data/processed/demand_classifications_nov2025_sep2026.parquet"
)

print(df["product_code"].astype(str).str.len().value_counts())
print(df["product_code"].head(10).to_list())
