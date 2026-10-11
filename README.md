# Emas Sentimen (scaffold 2026-10-11)

Adik dari `news_sentimen`, logika **berbeda**: emas itu safe-haven.

## Logika (SEARAH-TAKUT, kebalikan BTC)

- Berita jelek / takut (perang, resesi, dovish) => **bullish emas** => BELI
- Euforia tanpa takut => WASPADA
- Sisanya => HOLD

## Sumber (terverifikasi hidup 11 Okt 2026)

- Berita: FXStreet RSS (filter kata emas) + Fed press RSS
- Harga: Stooq XAUUSD harian, fallback Swissquote spot (keduanya tanpa key)

## Struktur

```
E:\emas/
  collect.py       ← RSS + VADER + harga → data/latest.json + gold_sentiment.json
  requirements.txt
```

## Status

- Live: https://120n1aja-emassentimen.static.hf.space/ (Space statis,
  upload manual via `export_static.py` + huggingface_hub, 12 Okt 2026).
- Jalankan lokal: `python E:\emas\dashboard.py` (:8005).
