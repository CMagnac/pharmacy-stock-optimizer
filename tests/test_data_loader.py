import pandas as pd

from pharmacy_stock.data_loader import load_inventory_csv


def test_load_inventory_csv(tmp_path):

    csv_file = tmp_path / "inventory.csv"

    csv_file.write_text(
        "Code produit;Désignation;Stock avant;Stock modifié\n"
        "123;TEST DRUG;2;3\n",
        encoding="utf-8",
    )

    df = load_inventory_csv(csv_file)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df["Code produit"].iloc[0] == "123"
