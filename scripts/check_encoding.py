from pathlib import Path


FILE = Path("data/raw/inventory_2026_08.csv")


def main():
    raw = FILE.read_bytes()

    print("First 300 bytes:")
    print(raw[:300])

    print("\nPossible decodings:")
    
    for encoding in ["utf-8", "utf-8-sig", "cp1252", "latin-1"]:
        try:
            text = raw.decode(encoding)
            first_line = text.splitlines()[0]
            print(f"\n{encoding}:")
            print(repr(first_line))
        except UnicodeDecodeError as error:
            print(f"\n{encoding}: FAILED")
            print(error)


if __name__ == "__main__":
    main()
