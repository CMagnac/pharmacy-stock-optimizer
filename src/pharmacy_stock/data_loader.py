from pathlib import Path

import pandas as pd


def load_inventory_csv(
    file_path: str | Path,
    encoding: str = "utf-8-sig",
) -> pd.DataFrame:
    """
    Load a pharmacy inventory CSV file.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Inventory file not found: {file_path}"
        )

    df = pd.read_csv(
        file_path,
        sep=";",
        decimal=",",
        encoding=encoding,
        dtype={
            "Code produit": "string",
        },
    )

    return df
