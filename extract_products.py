"""
Regenerates products.py (and the photos/ folder) from the website's
index.html catalog.

Usage:
    python extract_products.py path/to/index.html

Run this any time you update the product list or photos on the website and
want the Telegram bot to match it.
"""

import re
import os
import base64
import sys


def extract(html_path: str, out_path: str = "products.py", photos_dir: str = "photos"):
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

    # Extract embedded photos (base64 jpg) into individual files
    os.makedirs(photos_dir, exist_ok=True)
    photo_ids = set()
    for id_match in re.finditer(r"\{\s*id:(\d+),", html):
        pid = int(id_match.group(1))
        window = html[id_match.start(): id_match.start() + 120000]
        end = window.find("},\n")
        entry = window[:end] if end != -1 else window
        img_match = re.search(r"img:'data:image/jpeg;base64,([A-Za-z0-9+/=]+)'", entry)
        if img_match:
            data = base64.b64decode(img_match.group(1))
            with open(os.path.join(photos_dir, f"{pid}.jpg"), "wb") as f:
                f.write(data)
            photo_ids.add(pid)

    lines = [
        "# Auto-generated from the Dejaf Tadlu website catalog.",
        "# Re-run extract_products.py against index.html any time the site catalog changes,",
        "# or edit this list by hand -- either way keeps the bot and the site in sync.",
        "#",
        "# 'photo' points to a file in the photos/ folder (only present for items with a real",
        "# photo; items without one fall back to text-only display in the bot).",
        "",
        "PRODUCTS = [",
    ]
    for p in products:
        name = p["name"].replace("\\", "\\\\").replace('"', '\\"')
        cat = p["cat"].replace('"', '\\"')
        sale = "None" if p["sale"] is None else str(p["sale"])
        photo = f'"{photos_dir}/{p["id"]}.jpg"' if p["id"] in photo_ids else "None"
        lines.append(
            f'    {{"id": {p["id"]}, "name": "{name}", "cat": "{cat}", "price": {p["price"]}, '
            f'"sale": {sale}, "photo": {photo}}},'
        )
    lines.append("]")
    lines.append("")
    lines.append("CATEGORIES = sorted(set(p['cat'] for p in PRODUCTS))")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {len(products)} products ({len(photo_ids)} with photos) to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python extract_products.py path/to/index.html")
    extract(sys.argv[1])
