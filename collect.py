"""Kolektor sentimen EMAS (scaffold 2026-10-11, deploy TBD).

Sumber terverifikasi hidup:
  - FXStreet RSS  https://www.fxstreet.com/rss/news (filter kata emas)
  - Fed press RSS https://www.federalreserve.gov/feeds/press_all.xml
Harga: Stooq XAUUSD harian (fallback Swissquote spot, tanpa key).
Logika SEARAH-TAKUT (bukan kontrarian spt BTC): panic/geopolitik/
dovish => bullish emas. Output: data/latest.json + gold_sentiment.json
"""
import json
import os
import re
from datetime import datetime, timezone

import feedparser
import requests
import zipfile
import io
from nltk.sentiment import SentimentIntensityAnalyzer

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
LOGD = os.path.join(BASE, "logs")
os.makedirs(DATA, exist_ok=True)
os.makedirs(LOGD, exist_ok=True)

FEEDS = {
    "FXStreet": "https://www.fxstreet.com/rss/news",
    "FedPress": "https://www.federalreserve.gov/feeds/press_all.xml",
}
GOLD_API_KEY_FILE = os.path.join(BASE, "credential", "gold-api-com.key")
GOLD_WORDS = ("gold", "xau", "bullion", "safe-haven", "safe haven",
              "precious metal", "emas")
FEAR_WORDS = ("war", "conflict", "missile", "sanction", "crisis", "panic",
              "recession", "inflation", "rate cut", "dovish", "geopolitic",
              "default", "bank run", "uncertainty")
sia = SentimentIntensityAnalyzer()


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(LOGD, "collect.log"), "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def fetch_feed(name, url):
    out = []
    try:
        d = feedparser.parse(url,
                             agent="Mozilla/5.0 (emas-scaffold/1.0)")
        for e in d.entries[:30]:
            title = clean(getattr(e, "title", ""))
            summ = clean(getattr(e, "summary", "") or
                         getattr(e, "description", ""))[:500]
            blob = f"{title} {summ}".lower()
            if name == "FXStreet" and not any(
                    w in blob for w in GOLD_WORDS):
                continue
            comp = sia.polarity_scores(f"{title}. {summ}")["compound"]
            out.append({
                "source": name, "title": title[:300],
                "link": getattr(e, "link", ""),
                "published": getattr(e, "published", ""),
                "summary": summ,
                "compound": round(comp, 3),
                "fear": any(w in blob for w in FEAR_WORDS),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })
    except Exception as ex:
        log(f"{name} error: {ex}")
    log(f"{name}: {len(out)} artikel")
    return out


def cot_gold():
    """COT mingguan emas COMEX (managed money net). Cache per minggu.
    Return dict {date, mm_net, mm_net_chg} atau {} bila gagal."""
    cp = os.path.join(DATA, "cot_cache.json")
    cache = {}
    try:
        cache = json.load(open(cp, encoding="utf-8"))
    except Exception:
        pass
    wk = datetime.now(timezone.utc).strftime("%Y-W%V")
    if cache.get("week") == wk and cache.get("cot"):
        return cache["cot"]
    try:
        yr = datetime.now(timezone.utc).year
        url = ("https://www.cftc.gov/files/dea/history/"
               f"fut_disagg_txt_{yr}.zip")
        z = zipfile.ZipFile(io.BytesIO(requests.get(
            url, timeout=60).content))
        txt = z.read(z.namelist()[0]).decode("utf-8", "replace")
        import csv
        rows = [r for r in csv.reader(io.StringIO(txt))
                if r and r[0].strip().startswith("GOLD -")
                and "COMMODITY EXCHANGE" in r[0]]
        if not rows:
            return cache.get("cot", {})

        def num(x):
            try:
                return float((x or "").strip())
            except Exception:
                return 0.0

        hist = []
        # kolom disagg: 0 nama, 2 Report_Date, 7 OI, 13 MM long, 14 MM short
        for r in rows:
            mm_net = num(r[13]) - num(r[14])
            oi = num(r[7]) or 1.0
            hist.append({"date": r[2].strip(), "mm_net": int(mm_net),
                         "mm_pct_oi": round(mm_net / oi * 100, 1)})
        hist.sort(key=lambda h: h["date"])
        hist = hist[-8:]
        cot = hist[-1]
        cot["mm_chg_wow"] = (hist[-1]["mm_net"] - hist[-2]["mm_net"]
                             if len(hist) > 1 else 0)
        cache = {"week": wk, "cot": cot}
        json.dump(cache, open(cp, "w", encoding="utf-8"))
        log(f"COT emas {cot['date']}: MM net {cot['mm_net']} "
            f"({cot['mm_pct_oi']}% OI, WoW {cot['mm_chg_wow']:+})")
        return cot
    except Exception as ex:
        log(f"COT gagal: {ex}")
        return cache.get("cot", {})


def gold_price():
    """(harga, sumber). Swissquote spot dulu, Stooq harian cadangan."""
    try:
        d = requests.get("https://forex-data-feed.swissquote.com/"
                         "public-quotes/bboquotes/instrument/XAU/USD",
                         timeout=20).json()
        prof = d[0]["spreadProfilePrices"][0]
        return round((prof["bid"] + prof["ask"]) / 2, 2), "swissquote-spot"
    except Exception as ex:
        log(f"Swissquote gagal: {ex}")
    try:  # cadangan: gold-api.com gratis tanpa key (spot)
        d = requests.get("https://api.gold-api.com/price/XAU",
                         timeout=20).json()
        return round(float(d["price"]), 2), "gold-api"
    except Exception as ex:
        log(f"gold-api gagal: {ex}")
    try:
        r = requests.get("https://stooq.com/q/d/l/",
                         params={"s": "xauusd", "i": "d"},
                         headers={"User-Agent": "Mozilla/5.0"},
                         timeout=20)
        rows = [l for l in r.text.strip().splitlines() if l and
                not l.startswith("Date") and not l.startswith("<")]
        if rows:
            return float(rows[-1].split(",")[4]), "stooq"
    except Exception as ex:
        log(f"Stooq gagal: {ex}")
    return None, "none"


def main():
    log("=== Mulai koleksi emas ===")
    arts = []
    for name, url in FEEDS.items():
        arts += fetch_feed(name, url)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(os.path.join(DATA, f"gold_{ts}.json"), "w",
              encoding="utf-8") as f:
        json.dump(arts, f, indent=2, ensure_ascii=False)
    with open(os.path.join(DATA, "latest.json"), "w",
              encoding="utf-8") as f:
        json.dump(arts, f, indent=2, ensure_ascii=False)
    comps = [a["compound"] for a in arts]
    avg = sum(comps) / len(comps) if comps else 0.0
    fear_n = sum(1 for a in arts if a["fear"])
    price, src = gold_price()
    cot = cot_gold()
    # Vonis SEARAH-TAKUT: takut => bullish emas (kebalikan logika BTC)
    if avg <= -0.2 or fear_n >= 3:
        vonis = "BELI (takut = bullish emas)"
    elif avg >= 0.3 and fear_n == 0:
        vonis = "WASPADA (euforia = waspada)"
    else:
        vonis = "HOLD"
    summ = {"n": len(arts), "avg_compound": round(avg, 3),
            "fear_hits": fear_n, "vonis": vonis,
            "harga": price, "harga_src": src, "cot": cot,
            "waktu": datetime.now(timezone.utc).isoformat()}
    with open(os.path.join(DATA, "gold_sentiment.json"), "w",
              encoding="utf-8") as f:
        json.dump(summ, f, indent=2, ensure_ascii=False)
    if price:
        hist = []
        hp = os.path.join(DATA, "gold_price.json")
        try:
            hist = json.load(open(hp, encoding="utf-8"))
        except Exception:
            pass
        # sinkron histori harian gold-api.com (3 req: max/min/avg,
        # limit 10/jam). OHLC harian untuk ATR paper-trading.
        try:
            if os.path.exists(GOLD_API_KEY_FILE):
                key = open(GOLD_API_KEY_FILE,
                           encoding="utf-8").read().strip()
                now = int(datetime.now(timezone.utc).timestamp())
                series = {}
                for agg in ("max", "min", "avg"):
                    r = requests.get(
                        "https://api.gold-api.com/history",
                        params={"symbol": "XAU",
                                "startTimestamp": now - 60 * 86400,
                                "endTimestamp": now, "groupBy": "day",
                                "aggregation": agg, "orderBy": "asc"},
                        headers={"x-api-key": key}, timeout=25).json()
                    for row in r:
                        d = row["day"][:10]
                        series.setdefault(d, {})[agg] = float(
                            row[f"{agg}_price"])
                ohlc = [{"t": d + "T00:00:00+00:00", "h": v.get("max"),
                         "l": v.get("min"), "c": v.get("avg")}
                        for d, v in sorted(series.items())
                        if v.get("max") and v.get("min")]
                json.dump(ohlc, open(os.path.join(DATA, "gold_ohlc.json"),
                                     "w", encoding="utf-8"), indent=1)
                log(f"sinkron OHLC: {len(ohlc)} bar")
        except Exception as ex:
            log(f"sinkron histori gagal: {ex}")
        if not hist or (datetime.now(timezone.utc) -
                        datetime.fromisoformat(hist[-1]["t"])).total_seconds() > 6 * 3600:
            hist.append({"t": datetime.now(timezone.utc).isoformat(),
                         "price": price})
            hist = hist[-500:]
            json.dump(hist, open(hp, "w", encoding="utf-8"), indent=1)
            log(f"histori harga: {len(hist)} titik")
    log(f"Done: {len(arts)} artikel | vonis={vonis} | emas={price} ({src})")


if __name__ == "__main__":
    main()
