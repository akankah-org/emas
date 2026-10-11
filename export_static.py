"""Ekspor situs statis emas (untuk HF Static Space, gratis)."""
import json
import os
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from dashboard import HTML

STATIC = os.path.join(BASE, "static")
FILES = ["latest.json", "gold_sentiment.json", "gold_price.json",
         "gold_ohlc.json", "paper_gold_state.json", "paper_gold_trades.json",
         "paper_gold_equity.json", "near_miss_gold.json"]


def main():
    os.makedirs(os.path.join(STATIC, "data"), exist_ok=True)
    with open(os.path.join(STATIC, "index.html"), "w",
              encoding="utf-8") as f:
        f.write(HTML)
    n = 0
    for fn in FILES:
        src = os.path.join(BASE, "data", fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(STATIC, "data", fn))
            n += 1
    print(f"static/ siap: index.html + {n} JSON")


if __name__ == "__main__":
    main()
