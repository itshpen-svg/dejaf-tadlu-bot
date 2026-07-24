"""
Regenerates products.py from the website's tadlu-store.html catalog.

Usage:
    python extract_products.py path/to/tadlu-store.html

Run this any time you update the product list on the website and want the
Telegram bot to match it.
"""

import re
import sys


def extract(html_path: str, out_path: str = "products.py"):
    html = open(html_path, encoding="utf-8").read()
    m = re.search(r"const PRODUCTS = \[(.*?)\n  \];", html, re.S)
    if not m:
        raise SystemExit("Could not find the PRODUCTS array in that file.")
    block = m.group(1)

    pattern = re.compile(
        r"\{\s*id:(\d+),\s*name:(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"),"
        r"\s*cat:'((?:[^'\\]|\\.)*)',\s*price:(\d+),\s*sale:(null|\d+)"
    )

    products = []
    for pid, name1, name2, cat, price, sale in pattern.findall(block):
        name = (name1 or name2).replace("\\'", "'")
        cat = cat.replace("\\'", "'")
        products.append(
            {
                "id": int(pid),
                "name": name,
                "cat": cat,
                "price": int(price),
                "sale": None if sale == "null" else int(sale),
            }
        )

    lines = [
        "# Auto-generated from the Dejaf Tadlu website catalog.",
        "# Re-run extract_products.py against tadlu-store.html any time the site catalog changes,",
        "# or edit this list by hand -- either way keeps the bot and the site in sync.",
        "",
        "PRODUCTS = [",
    ]
    for p in products:
        name = p["name"].replace("\\", "\\\\").replace('"', '\\"')
        cat = p["cat"].replace('"', '\\"')
        sale = "None" if p["sale"] is None else str(p["sale"])
        lines.append(
            f'    {{"id": {p["id"]}, "name": "{name}", "cat": "{cat}", "price": {p["price"]}, "sale": {sale}}},'
        )
    lines.append("]")
    lines.append("")
    lines.append("CATEGORIES = sorted(set(p['cat'] for p in PRODUCTS))")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {len(products)} products to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python extract_products.py path/to/tadlu-store.html")
    extract(sys.argv[1])
