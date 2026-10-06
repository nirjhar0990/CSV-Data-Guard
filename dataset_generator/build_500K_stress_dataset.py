import pandas as pd
from pathlib import Path

SOURCE = Path("data/messy_retail_data_250K.csv")
OUTPUT = Path("data/messy_retail_data_500K.csv")

def remap_order_id(value):
    text = str(value)
    if (
        len(text) == 9
        and text.startswith("ORD-")
        and text[4:].isdigit()
    ):
        number = int(text[4:])
        number = ((number * 37 + 17011) % 100000)
        return f"ORD-{number:05d}"
    return value

def main():
    print("\n==============================================")
    print(" CSV DATA GUARD - BUILD 500K STRESS DATASET")
    print("==============================================")
    print("Source:", SOURCE)

    if not SOURCE.exists():
        raise FileNotFoundError(f"Source dataset not found: {SOURCE}")

    first = pd.read_csv(SOURCE, keep_default_na=False)

    if len(first) != 250000:
        raise ValueError(
            f"Expected exactly 250000 rows in source dataset, found {len(first)}."
        )

    second = first.copy(deep=True)
    second["Order_ID"] = second["Order_ID"].map(remap_order_id)

    combined = pd.concat([first, second], ignore_index=True)

    if len(combined) != 500000:
        raise AssertionError(f"Expected 500000 rows, got {len(combined)}.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT, index=False)

    print("Rows:", len(combined))
    print("Columns:", len(combined.columns))
    print("Output:", OUTPUT)
    print("\n500K stress dataset created successfully.")

if __name__ == "__main__":
    main()
