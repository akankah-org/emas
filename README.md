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
- UI rapi 12 Okt: Vonis + Vonis-ST terpisah, sentimen/fear/COT di
  dalam Vonis, berita paling bawah, 2 kartu logika, 2 paper + BH.
- Notif: digest data via @Lampu_emas_bot, status refresh via
  @Opencodekubot (kunci di vault, secret di repo).
- Jalankan lokal: `python E:\emas\dashboard.py` (:8005).

## Aturan Main Dua Kartu (12 Okt, keputusan user)

- Juara = **return % terbesar** (BEST card).
- Syarat ikut dinilai: ≥30 trade + expectancy positif + DD <20% +
  kalahkan buy-and-hold. Belum lolos = "belum dinilai".
- Pemenang + persetujuan eksplisit user = kandidat bot live
  (API trade-only + dana kecil + kill-switch).

## Dua Paper (12 Okt)

- 📄 Paper: sinyal vonis sentimen (searah-takut), LONG-only.
- 📄 Paper-ST: supertrend p=10/m=0,3 (finder TEST +1,1% n=9).
  Prinsip: pasar satu, juri dua.
