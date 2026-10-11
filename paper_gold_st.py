"""Paper-trading EMAS #2: SUPERTREND finder (SIMULASI, BUKAN uang beneran).

Param dari finder disiplin 12 Okt (24 varian, TRAIN emas harian):
p=10, m=0.3, sl=5%, trail act=1.0/dist=0.3. Status: TEST +1,1% (9 trade)
-> BELUM tervalidasi kuat. LONG-only (sama mesin tune).
Sinyal: flip-up + filter harga>ST + linreg. Kelola 1x/hari.
File terpisah (*_st) + laporan terpisah di dashboard.

JAMINAN: hanya BACA + HITUNG + CATAT. Nol kode order.
"""
import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
STATE = os.path.join(DATA, "paper_st_state.json")
TRADES = os.path.join(DATA, "paper_st_trades.json")
EQUITY = os.path.join(DATA, "paper_st_equity.json")
OHLC = os.path.join(DATA, "gold_ohlc.json")

P, M = 10, 0.3
EQUITY0 = 10000.0
RISK_PCT = 0.01
STOP_ATR = 1.5
TP_R = 2.0
FEE = 0.001
SLIP = 0.0005
SL_PCT, TRAIL_ACT, TRAIL_DIST = 5.0, 1.0, 0.3
RULES = "st-p10m03-2026-10-12"


def load(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def linreg_line(closes, n=20):
    if len(closes) < n:
        return None
    y = closes[-n:]
    x = list(range(n))
    mx, my = sum(x) / n, sum(y) / n
    den = sum((xi - mx) ** 2 for xi in x) or 1.0
    b = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / den
    return my + b * (n - 1)


def supertrend(hi, lo, cl, period, mult):
    """Supertrend pure-python, port 1:1 dari tune (Wilder ATR)."""
    n = len(cl)
    tr = [hi[0] - lo[0]] + [
        max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1]))
        for i in range(1, n)]
    atr = [None] * n
    if n >= period:
        atr[period - 1] = sum(tr[:period]) / period
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    trend, stl = [0] * n, [0.0] * n
    s = period - 1
    if s >= n or not atr[s]:
        return trend, stl
    up = (hi[s] + lo[s]) / 2 + mult * atr[s]
    dn = (hi[s] + lo[s]) / 2 - mult * atr[s]
    if cl[s] > up:
        trend[s], stl[s] = 1, dn
    elif cl[s] < dn:
        trend[s], stl[s] = -1, up
    else:
        trend[s], stl[s] = 1, dn
    for i in range(s + 1, n):
        if not atr[i]:
            trend[i], stl[i] = trend[i - 1], stl[i - 1]
            continue
        if cl[i] > (hi[i - 1] + lo[i - 1]) / 2 + mult * atr[i - 1]:
            trend[i] = 1
        elif cl[i] < (hi[i - 1] + lo[i - 1]) / 2 - mult * atr[i - 1]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]
        up = (hi[i] + lo[i]) / 2 + mult * atr[i]
        dn = (hi[i] + lo[i]) / 2 - mult * atr[i]
        stl[i] = dn if trend[i] == 1 else up
    return trend, stl


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    st = load(STATE, {"equity": EQUITY0, "open": None,
                      "managed_date": None, "started": today})
    if st.get("managed_date") == today:
        print(f"paper-st {today}: sudah dikelola, skip")
        return
    bars = load(OHLC, [])
    if len(bars) < P + 5:
        print("paper-st: histori kurang")
        return
    h = [b["h"] for b in bars]
    lo = [b["l"] for b in bars]
    c = [b["c"] for b in bars]
    trend, stl = supertrend(h, lo, c, P, M)
    day = bars[-1]
    a = float(np.mean([b["h"] - b["l"] for b in bars[-14:]]))
    eq = st["equity"]
    trades = load(TRADES, [])
    equity = load(EQUITY, [])
    flip_up = trend[-2] == -1 and trend[-1] == 1
    flip_down = trend[-2] == 1 and trend[-1] == -1
    st["signal"] = {"trend": "BULLISH" if trend[-1] == 1 else "BEARISH",
                    "st": round(float(stl[-1]), 2), "date": today,
                    "flip": "UP" if flip_up else ("DOWN" if flip_down
                                                  else "-")}

    op = st.get("open")
    if op:
        peak = max(op.get("peak", op["entry"]), day["h"])
        op["peak"] = peak
        tstop = peak * (1 - TRAIL_DIST / 100)
        if (peak - op["entry"]) / op["entry"] * 100 >= TRAIL_ACT \
                and tstop > op["stop"]:
            op["stop"] = tstop
            op["trailed"] = True
        closed, alasan, px = None, "", 0.0
        if day["l"] <= op["stop"]:
            closed, alasan, px = True, \
                ("trail" if op.get("trailed") else "stop"), op["stop"]
        elif day["h"] >= op["tp"]:
            closed, alasan, px = True, "tp", op["tp"]
        elif flip_down:
            closed, alasan, px = True, "flip", day["c"] * (1 - SLIP)
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
            print(f"paper-st {today}: tutup {alasan} pnl={pnl:.2f}")

    if st.get("open") is None and flip_up:
        stl_i = float(stl[-1])
        ok = True
        if stl_i > 0:
            dist = (c[-1] - stl_i) / stl_i * 100
            ok = dist >= 0.05 and dist <= 2.0 and c[-1] > stl_i
        lr = linreg_line(list(c))
        if lr is not None and not c[-1] > lr:
            ok = False
        if ok and a > 0:
            risk_amt = RISK_PCT * eq
            qty = risk_amt / (STOP_ATR * a)
            if qty * c[-1] > eq:
                qty = eq / c[-1]
            entry = c[-1] * (1 + SLIP)
            st["open"] = {"qty": qty, "entry": entry,
                          "stop": entry * (1 - SL_PCT / 100),
                          "tp": 0.0, "peak": entry, "trailed": False,
                          "date": today, "risk_amt": risk_amt,
                          "rules": RULES}
            eq -= qty * entry * FEE
            print(f"paper-st {today}: buka LONG-ST @{entry:.2f}")

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
    print(f"paper-st {today}: eq={eq:.2f} trade={n} win={w}")


if __name__ == "__main__":
    main()
