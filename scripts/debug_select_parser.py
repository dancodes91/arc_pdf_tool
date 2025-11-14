import pandas as pd

from parsers.select.parser import SelectHingesParser


def main() -> None:
    pdf_path = r"c:\Users\Vache\Desktop\vatche\arc_pdf_tool\test_data\pdfs\2025-select-hinges-price-book.pdf"

    parser = SelectHingesParser(
        pdf_path,
        config={
            "camelot_timeout": 30,
            "enable_camelot": True,
            "camelot_flavors": ["stream", "lattice"],
        },
    )

    result = parser.parse()
    products = result.get("products", [])
    print("TOTAL PRODUCTS:", len(products))

    rows = []
    for item in products:
        value = item.get("value", {})
        if not isinstance(value, dict):
            continue

        specs = value.get("specifications", {}) or {}
        rows.append(
            {
                "sku": value.get("sku"),
                "model": value.get("model"),
                "length": specs.get("length"),
                "base_price": value.get("base_price"),
            }
        )

    df = pd.DataFrame(rows)
    print(df.head(80).to_string())

    # Helpful filters for debugging specific issues
    for pattern in ["SL11", "SL12", "SL14", "SL18"]:
        mask = df["sku"].astype(str).str.contains(pattern, na=False)
        print(f"\nRows matching {pattern}:")
        print(df[mask].to_string())


if __name__ == "__main__":
    main()

