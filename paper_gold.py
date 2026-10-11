"""Paper-trading EMAS (SIMULASI di atas data live — BUKAN uang beneran).

Sinyal: vonis BELI dari gold_sentiment.json (logika searah-takut) -> LONG
virtual. Tak ada SHORT (tak dirancang untuk emas). Kelola 1x per tanggal
UTC pakai bar harian gold_ohlc.json, aturan TERKUNCI (risiko 1%,
stop 1,5xATR-14, TP 2R, fee 0,1%/slip 0,05%, maks 1 posisi, tanpa leverage).
Baseline pembanding: buy-and-hold (dihitung dashboard dari start_xau).

JAMINAN: hanya BACA + HITUNG + CATAT. Nol kode order, nol API key
exchange, nol koneksi akun.
GARANSI-UJI: grep -riE "create_order|place_order|api[_-]?secret" paper_gold.py
"""
import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
STATE = os.path.join(DATA, "paper_gold_state.json")
TRADES = os.path.join(DATA, "paper_gold_trades.json")
EQUITY = os.path.join(DATA, "paper_gold_equity.json")
SENT = os.path.join(DATA, "gold_sentiment.json")
OHLC = os.path.join(DATA, "gold_ohlc.json")

EQUITY0 = 10000.0
RISK_PCT = 0.01
STOP_ATR = 1.5
TP_R = 2.0
FEE = 0.001
SLIP = 0.0005


def load(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def atr(bars, n=14):
    if len(bars) < n + 1:
        return None
    trs = []
    for i, b in enumerate(bars):
        pc = bars[i - 1]["c"] if i else b["c"]
        trs.append(max(b["h"] - b["l"], abs(b["h"] - pc),
                       abs(b["l"] - pc)))
    return sum(trs[-n:]) / n


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    st = load(STATE, {"equity": EQUITY0, "open": None,
                      "managed_date": None, "started": today})
    if st.get("managed_date") == today:
        print(f"paper-gold {today}: sudah dikelola, skip")
        return
    sent = load(SENT, {})
    bars = load(OHLC, [])
    if len(bars) < 16:
        print("paper-gold: histori kurang (butuh >=16 bar)")
        return
    day = bars[-1]
    a = atr(bars)
    eq = st["equity"]
    trades = load(TRADES, [])
    equity = load(EQUITY, [])

    op = st.get("open")
    if op:
        closed, alasan, px = None, "", 0.0
        if day["l"] <= op["stop"]:
            closed, alasan, px = True, "stop", op["stop"]
        elif day["h"] >= op["tp"]:
            closed, alasan, px = True, "tp", op["tp"]
        if closed:
            qty = op["qty"]
            gross = qty * (px - op["entry"])
            pnl = gross - (qty * op["entry"] + qty * px) * (FEE + SLIP)
            trades.append({
                "entry_tgl": op["date"], "entry": round(op["entry"], 2),
                "exit_tgl": today, "exit": round(px, 2),
                "qty": round(qty, 4), "alasan": alasan,
                "pnl": round(pnl, 2),
                "r": round(pnl / op["risk_amt"], 2),
            })
            eq += pnl
            st["open"] = None
            print(f"paper-gold {today}: tutup {alasan} pnl={pnl:.2f}")

    if st.get("open") is None and a:
        fire = (sent.get("vonis") or "").startswith("BELI")
        if fire:
            c = day["c"]
            risk_amt = RISK_PCT * eq
            qty = risk_amt / (STOP_ATR * a)
            if qty * c > eq:
                qty = eq / c
            entry = c * (1 + SLIP)
            st["open"] = {"qty": qty, "entry": entry,
                          "stop": entry - STOP_ATR * a,
                          "tp": entry + TP_R * STOP_ATR * a,
                          "date": today, "risk_amt": risk_amt}
            eq -= qty * entry * FEE
            print(f"paper-gold {today}: buka LONG @{entry:.2f}")

    st["equity"] = eq
    st["managed_date"] = today
    if "start_xau" not in st:
        st["start_xau"] = day["c"]
    equity.append({"date": today, "eq": round(eq, 2)})
    save(STATE, st)
    save(TRADES, trades)
    save(EQUITY, equity)
    n = len(trades)
    w = sum(1 for t in trades if t["pnl"] > 0)
    print(f"paper-gold {today}: eq={eq:.2f} trade={n} win={w}")


if __name__ == "__main__":
    main()
