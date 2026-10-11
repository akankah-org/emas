import json
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PORT = int(os.getenv("PORT", "8005"))

HTML = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Emas Sentiment</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}
h1{color:#e3b341;margin-bottom:5px}
.sub{color:#8b949e;font-size:14px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;margin-bottom:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px}
.card h2{font-size:14px;color:#8b949e;text-transform:uppercase;margin-bottom:8px}
.card .val{font-size:32px;font-weight:700}
.card .val.pos{color:#3fb950}
.card .val.neg{color:#f85149}
.card .val.neu{color:#e3b341}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.badge.pos{background:#3fb95033;color:#3fb950}
.badge.neg{background:#f8514933;color:#f85149}
.badge.neu{background:#e3b34133;color:#e3b341}
.article{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:15px;margin-bottom:10px}
.article .source{font-size:11px;color:#8b949e}
.article .title{font-size:15px;color:#e6edf3;margin:5px 0}
.article .title a{color:#e6edf3;text-decoration:none}
.article .title a:hover{color:#e3b341}
.article .summary{font-size:13px;color:#8b949e;margin-top:5px}
.footer{text-align:center;color:#8b949e;font-size:12px;margin-top:20px}
@media(max-width:600px){body{padding:10px}.card .val{font-size:24px}}
</style>
</head>
<body>
<h1>🪙 Emas Sentiment</h1>
<p class="sub" id="sub">Loading...</p>
<div class="grid" id="gold-cards"></div>
<div class="card" style="margin-bottom:20px"><h2>Teknikal (hitung sendiri)</h2>
<div id="gold-ta" style="font-size:13px;line-height:1.8">Memuat…</div></div>
<div class="card" style="margin-bottom:20px"><h2>Cara Baca COT (Managed Money)</h2>
<div style="font-size:13px;line-height:1.8">
<b>MM Net</b> = kontrak long − short spekulan besar (COMEX). <b>% OI</b> = seberapa berdesakan mereka. <b>WoW</b> = perubahan vs Selasa lalu.<br>
🟢 Net naik + % OI naik = crowd makin bullish → <b>ikuti tapi waspada puncak</b>.<br>
🟡 Net turun dari puncak (seperti sekarang +110rb tapi WoW −9rb) = crowd <b>memangkas</b> → jangan tambah posisi, tunggu.<br>
🔴 Net negatif = spekulan net short (langka) → <b>contrarian bullish</b>: bahan bakar short-squeeze.<br>
<span style="color:#8b949e">Batasan: data potret Selasa, terbit Jumat (3 hari basi); cuma futures AS, tak lihat spot LBMA. Kaki konfirmasi, bukan pemicu entry.</span>
</div></div>
<div class="card" style="margin-bottom:20px"><h2>Harga Emas (7 hari, data sendiri)</h2>
<div style="max-width:700px;margin:0 auto"><canvas id="goldChart"></canvas></div>
<div id="gold-chart-note" style="font-size:12px;color:#8b949e;text-align:center"></div></div>
<div class="card" style="margin-bottom:20px"><h2>Logika: SEARAH-TAKUT</h2>
<div style="font-size:13px;line-height:1.7;color:#8b949e">Takut (perang, resesi, dovish) = bullish emas → <strong>BELI</strong>. Euforia tanpa takut = WASPADA. Kebalikan logika BTC yang kontrarian.</div></div>
<h2>Berita Emas</h2>
<div id="news-list"></div>
<div id="news-more" style="text-align:center;color:#8b949e;font-size:13px;padding:10px"></div>
<div class="card" style="margin-bottom:20px" id="paper"><h2>📄 Paper Bot Emas (SIMULASI)</h2>
<div id="paper-stats" style="font-size:13px;line-height:1.8">Memuat…</div>
<div style="max-width:700px;margin:10px auto"><canvas id="paperChart"></canvas></div>
<div id="paper-trades" style="font-size:13px;overflow-x:auto">-</div>
<div style="font-size:12px;color:#8b949e;margin-top:8px">Aturan: LONG saat vonis BELI · risiko 1% · stop 1,5×ATR-14 · TP 2R · tanpa leverage · dievaluasi setelah ≥30 trade vs buy-and-hold.</div></div>
<div class="card" style="margin-bottom:20px" id="paperst"><h2>📄 Paper-ST Supertrend (SIMULASI)</h2>
<div id="paperst-stats" style="font-size:13px;line-height:1.8">Memuat…</div>
<div id="paperst-trades" style="font-size:13px;overflow-x:auto">-</div>
<div style="font-size:12px;color:#8b949e;margin-top:8px">Param finder p=10/m=0,3 (TEST +1,1%, n=9 — BELUM validasi kuat) · LONG-only · dievaluasi setelah ≥30 trade vs buy-and-hold.</div></div>
<div class="card" style="margin-bottom:20px"><h2>Uji Musiman (live)</h2><div id="season-test" style="font-size:13px;line-height:1.8">Memuat…</div>
<div style="font-size:12px;color:#8b949e;margin-top:8px">Klaim: Jan +5% (bullish) · Sep KONFLIKS (sumber trader: bearish 90% dekade terakhir vs paper SSRN: +2,23% terbaik) · Q1 positif 70% (20 thn) · Jul positif 65%. Bulan tanpa klaim = tak dinilai. Skor dari histori harga sendiri.</div></div>
<p class="footer">FXStreet + Fed Press | Harga Swissquote spot | Lokal PC (tanpa kuota)</p>
<script>
async function load() {
  const bust = '?t=' + Date.now();
  const CLAIMS = { 0: {bias: 'bullish', label: 'Jan +5% avg 20 thn'},
    6: {bias: 'bullish', label: 'Jul positif 65%'} };
  try {
    const hist = await fetch('data/gold_price.json' + bust).then(r=>r.json());
    const now = new Date();
    const m = now.getMonth(), y = now.getFullYear();
    const mp = hist.filter(p => { const d = new Date(p.t); return d.getMonth() === m && d.getFullYear() === y; });
    let html = '';
    if (mp.length >= 2) {
      const mtd = (mp[mp.length-1].price / mp[0].price - 1) * 100;
      const cl = CLAIMS[m];
      if (cl) {
        const ok = (cl.bias === 'bullish' && mtd > 0) || (cl.bias === 'bearish' && mtd < 0);
        html = `<strong>Bulan ini:</strong> klaim "${cl.label}" → realita MTD <strong style="color:${mtd>=0?'#3fb950':'#f85149'}">${mtd>=0?'+':''}${mtd.toFixed(1)}%</strong> = ${ok ? '✅ BENAR (sementara)' : '❌ SALAH (sementara)'}`;
      } else {
        html = `<strong>Bulan ini:</strong> tak ada klaim musiman → tak dinilai. Realita MTD <strong>${mtd>=0?'+':''}${mtd.toFixed(1)}%</strong> (catat saja).`;
      }
    } else {
      html = 'Belum cukup titik bulan ini untuk menilai.';
    }
    // skor bulan-bulan lalu yang punya klaim penuh
    const done = [];
    [0, 6].forEach(mm => {
      const yrs = [...new Set(hist.map(p => new Date(p.t).getFullYear()))];
      yrs.forEach(yy => {
        const pts = hist.filter(p => { const d = new Date(p.t); return d.getMonth() === mm && d.getFullYear() === yy; });
        if (pts.length >= 20 && !(mm === m && yy === y)) {
          const r = (pts[pts.length-1].price / pts[0].price - 1) * 100;
          const ok = r > 0;
          done.push(`${['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'][mm]} ${yy}: ${r>=0?'+':''}${r.toFixed(1)}% ${ok?'✅':'❌'}`);
        }
      });
    });
    if (done.length) html += '<br><strong>Verifikasi selesai:</strong><br>' + done.join('<br>');
    else html += '<br><em>Belum ada bulan terklaim yang lengkap — verifikasi pertama menunggu.</em>';
    document.getElementById('season-test').innerHTML = html;
    // teknikal sendiri dari histori: RSI-14 + SMA20/50
    try {
      const cl = hist.map(p => p.price);
      const rsi = (c, n=14) => {
        if (c.length < n + 1) return null;
        let g = 0, l = 0;
        for (let i = 1; i <= n; i++) { const d = c[i] - c[i-1]; if (d > 0) g += d; else l -= d; }
        g /= n; l /= n;
        for (let i = n + 1; i < c.length; i++) { const d = c[i] - c[i-1]; g = (g * (n-1) + Math.max(d, 0)) / n; l = (l * (n-1) + Math.max(-d, 0)) / n; }
        return l === 0 ? 100 : Math.round((100 - 100 / (1 + g / l)) * 10) / 10;
      };
      const sma = (c, n) => c.length >= n ? Math.round(c.slice(-n).reduce((s, v) => s + v, 0) / n * 10) / 10 : null;
      const r = rsi(cl), s20 = sma(cl, 20), s50 = sma(cl, 50), last = cl[cl.length-1];
      const tren = (s20 && last > s20) ? 'di atas SMA20 (bias naik)' : (s20 ? 'di bawah SMA20 (bias turun)' : 'belum cukup data');
      const rk = r === null ? 'belum cukup data' : (r > 70 ? 'OVERBOUGHT (>70)' : (r < 30 ? 'OVERSOLD (<30)' : 'netral')) + ` (${r})`;
      // banding: Investing.com 2 hari lalu RSI 63,1
      document.getElementById('gold-ta').innerHTML =
        `RSI-14: <strong>${rk}</strong> · Harga $${last.toLocaleString()} ${tren}` +
        (s20 ? ` · SMA20 $${s20.toLocaleString()}` : '') + (s50 ? ` · SMA50 $${s50.toLocaleString()}` : ' · SMA50 menunggu 50 titik') +
        `<br><span style="color:#8b949e">Acuan luar: Investing.com 2 hari lalu RSI 63,1 / MACD 12,8. <a href="https://www.tradingview.com/symbols/XAUUSD/technicals/" target="_blank">Teknikal TradingView →</a></span>`;
    } catch(e) { document.getElementById('gold-ta').textContent = 'Gagal hitung.'; }
    const pts = hist.slice(-40);
    if (pts.length >= 2) {
      document.getElementById('gold-chart-note').textContent =
        `${pts.length} titik (histori sendiri sejak ${pts[0].t.slice(0, 10)})`;
      new Chart(document.getElementById('goldChart'), { type: 'line',
        data: { labels: pts.map(p=>p.t.slice(5, 16).replace('T', ' ')),
          datasets: [{ label: 'XAU/USD', data: pts.map(p=>p.price),
            borderColor: '#e3b341', pointRadius: 2 }] },
        options: { plugins: { legend: { labels: { color: '#c9d1d9' } } },
          scales: { x: { ticks: { color: '#8b949e', maxTicksLimit: 8 } },
            y: { ticks: { color: '#8b949e' } } } } });
    } else {
      document.getElementById('gold-chart-note').textContent =
        'Mengumpulkan histori… grafik hidup setelah beberapa kali run.';
    }
  } catch(e) {
    document.getElementById('gold-chart-note').textContent = 'Belum ada histori harga.';
  }
  const [news, sent, sst0] = await Promise.all([
    fetch('data/latest.json' + bust).then(r=>r.json()),
    fetch('data/gold_sentiment.json' + bust).then(r=>r.json()),
    fetch('data/paper_st_state.json' + bust).then(r=>r.json()).catch(()=>null)
  ]);
  const stTrend = sst0 && sst0.signal ? sst0.signal.trend : null;
  const stc = stTrend === 'BULLISH' ? 'pos' : (stTrend === 'BEARISH' ? 'neg' : 'neu');
  document.getElementById('sub').textContent = `Update: ${new Date(sent.waktu).toLocaleString()} | ${sent.n} artikel`;
  const vc = sent.vonis.startsWith('BELI') ? 'pos' : (sent.vonis.startsWith('WASPADA') ? 'neg' : 'neu');
  let idr = '<div style="font-size:12px;color:#8b949e">kurs memuat…</div>';
  try {
    let rate = 0;
    try {
      const fx = await fetch('https://open.er-api.com/v6/latest/USD').then(r=>r.json());
      rate = fx.rates && fx.rates.IDR;
    } catch(e) {}
    if (!rate) {
      const fx2 = await fetch('https://api.frankfurter.app/latest?from=USD&to=IDR').then(r=>r.json());
      rate = fx2.rates && fx2.rates.IDR;
    }
    if (rate && sent.harga)
      idr = `<div style="font-size:12px;color:#8b949e">≈ Rp ${Math.round(sent.harga * rate).toLocaleString('id-ID')} <span style="font-size:11px">(USD/IDR ${Math.round(rate).toLocaleString('id-ID')})</span></div>`;
    else
      idr = '';
  } catch(e) { idr = ''; }
  document.getElementById('gold-cards').innerHTML = `
    <div class="card"><h2>Harga Emas (XAU)</h2><div class="val neu">$${sent.harga?.toLocaleString() || '?'}</div><div style="font-size:12px;color:#8b949e">${sent.harga_src || ''}</div>${idr}</div>
    <div class="card"><h2>Vonis</h2><div class="val ${vc}" style="font-size:22px">${sent.vonis}</div>${stTrend ? `<div class="val ${stc}" style="font-size:16px;margin-top:6px">ST: ${stTrend}</div>` : ''}</div>
    <div class="card"><h2>Sentimen Rata2</h2><div class="val ${sent.avg_compound < 0 ? 'neg' : 'pos'}">${sent.avg_compound}</div></div>
    <div class="card"><h2>Fear Hits</h2><div class="val ${sent.fear_hits > 0 ? 'neg' : 'neu'}">${sent.fear_hits}</div></div>
    <div class="card" id="paper-mini"><h2>📄 Paper</h2><div class="val neu">…</div></div>
    <div class="card" id="paperst-mini"><h2>📄 Paper-ST</h2><div class="val neu">…</div></div>
    ${sent.cot && sent.cot.date ? `<div class="card"><h2>COT MM Net (${sent.cot.date.slice(5)})</h2><div class="val ${sent.cot.mm_net >= 0 ? 'pos' : 'neg'}">${sent.cot.mm_net >= 0 ? '+' : ''}${sent.cot.mm_net.toLocaleString()}</div><div style="font-size:12px;color:#8b949e">${sent.cot.mm_pct_oi}% OI · WoW ${sent.cot.mm_chg_wow >= 0 ? '+' : ''}${sent.cot.mm_chg_wow.toLocaleString()} (CFTC, tiap Selasa)</div></div>` : ''}
  `;
  try {
    const [pst, ptr, pequ] = await Promise.all([
      fetch('data/paper_gold_state.json' + bust).then(r=>r.json()).catch(()=>null),
      fetch('data/paper_gold_trades.json' + bust).then(r=>r.json()).catch(()=>[]),
      fetch('data/paper_gold_equity.json' + bust).then(r=>r.json()).catch(()=>[])
    ]);
    const pxhist = await fetch('data/gold_price.json' + bust).then(r=>r.json()).catch(()=>[]);
    if (pst) {
      const ret = (pst.equity / 10000 - 1) * 100;
      document.getElementById('paper-mini').innerHTML =
        `<h2><a href="#paper" style="color:#8b949e;text-decoration:none">📄 Paper →</a></h2><div class="val ${ret >= 0 ? 'pos' : 'neg'}">${ret >= 0 ? '+' : ''}${ret.toFixed(1)}%</div><div style="font-size:12px;color:#8b949e">Vonis: <strong>${sent.vonis || '?'}</strong></div><div style="font-size:12px;color:#8b949e">${ptr.length} trade${pst.open ? ' · <strong>OPEN</strong>' : ''}</div>`;
      const n = ptr.length, w = ptr.filter(t => t.pnl > 0).length;
      const gp = ptr.filter(t => t.pnl > 0).reduce((s, t) => s + t.pnl, 0);
      const gl = -ptr.filter(t => t.pnl <= 0).reduce((s, t) => s + t.pnl, 0) || 1e-9;
      const pxmap = {};
      pxhist.forEach(p => { pxmap[p.t.slice(0, 10)] = p.price; });
      const bh = pequ.map(p => pxmap[p.date] && pst.start_xau ? Math.round(10000 * pxmap[p.date] / pst.start_xau * 100) / 100 : null);
      document.getElementById('paper-stats').innerHTML =
        `Ekuitas <strong>$${Math.round(pst.equity).toLocaleString()}</strong> (${ret >= 0 ? '+' : ''}${ret.toFixed(1)}%) · Trade ${n} · Win ${w} · PF ${(gp / gl).toFixed(2)} · Mulai ${pst.started || '-'}${pst.open ? ` · <strong style="color:#e3b341">OPEN LONG @ $${pst.open.entry.toLocaleString()}</strong>` : ' · flat (HOLD)'}`;
      document.getElementById('paper-trades').innerHTML = n
        ? `<table style="width:100%;border-collapse:collapse;font-size:12px"><tr style="color:#8b949e"><th align="left">Masuk</th><th align="right">Entry</th><th align="right">Exit</th><th align="right">PnL</th><th align="right">R</th><th>Keluar</th></tr>` +
          ptr.slice(-10).reverse().map(t => `<tr><td>${t.entry_tgl}</td><td align="right">$${t.entry.toLocaleString()}</td><td align="right">$${t.exit.toLocaleString()}</td><td align="right" style="color:${t.pnl > 0 ? '#3fb950' : '#f85149'}">${t.pnl > 0 ? '+' : ''}${t.pnl}</td><td align="right">${t.r}</td><td>${t.alasan}</td></tr>`).join('') + `</table>`
        : 'Belum ada trade (menunggu vonis BELI pertama).';
      if (pequ.length >= 1) {
        new Chart(document.getElementById('paperChart'), { type: 'line',
          data: { labels: pequ.map(p => p.date.slice(5)),
            datasets: [
              { label: 'Paper ($)', data: pequ.map(p => p.eq), borderColor: '#e3b341', pointRadius: 2 },
              { label: 'Buy-and-hold ($)', data: bh, borderColor: '#58a6ff', borderDash: [5, 5], pointRadius: 0 }] },
          options: { plugins: { legend: { labels: { color: '#c9d1d9' } } },
            scales: { x: { ticks: { color: '#8b949e', maxTicksLimit: 8 } }, y: { ticks: { color: '#8b949e' } } } } });
      }
    } else {
      document.getElementById('paper-stats').textContent = 'paper_bot belum pernah jalan.';
    }
  } catch(e) { document.getElementById('paper-stats').textContent = 'Gagal muat paper.'; }
  try {
    const [sst, str, sequ] = await Promise.all([
      fetch('data/paper_st_state.json' + bust).then(r=>r.json()).catch(()=>null),
      fetch('data/paper_st_trades.json' + bust).then(r=>r.json()).catch(()=>[]),
      fetch('data/paper_st_equity.json' + bust).then(r=>r.json()).catch(()=>[])
    ]);
    if (sst) {
      const sret = (sst.equity / 10000 - 1) * 100;
      document.getElementById('paperst-mini').innerHTML =
        `<h2><a href="#paperst" style="color:#8b949e;text-decoration:none">📄 Paper-ST →</a></h2><div class="val ${sret >= 0 ? 'pos' : 'neg'}">${sret >= 0 ? '+' : ''}${sret.toFixed(1)}%</div><div style="font-size:12px;color:#8b949e">Vonis-ST: <strong>${sst.signal ? sst.signal.trend : '?'}</strong></div><div style="font-size:12px;color:#8b949e">${str.length} trade${sst.open ? ' · <strong>OPEN</strong>' : ''}</div>`;
      const sn = str.length, sw = str.filter(t => t.pnl > 0).length;
      const sgp = str.filter(t => t.pnl > 0).reduce((s, t) => s + t.pnl, 0);
      const sgl = -str.filter(t => t.pnl <= 0).reduce((s, t) => s + t.pnl, 0) || 1e-9;
      document.getElementById('paperst-stats').innerHTML =
        `Vonis-ST: <strong style="color:${sst.signal && sst.signal.trend === 'BULLISH' ? '#3fb950' : '#f85149'}">${sst.signal ? sst.signal.trend : '?'}</strong> <span style="color:#8b949e">(ST $${sst.signal ? sst.signal.st.toLocaleString() : '?'}, flip ${sst.signal ? sst.signal.flip : '?'}, ${sst.signal ? sst.signal.date : ''})</span><br>Ekuitas <strong>$${Math.round(sst.equity).toLocaleString()}</strong> (${sret >= 0 ? '+' : ''}${sret.toFixed(1)}%) · Trade ${sn} · Win ${sw} · PF ${(sgp / sgl).toFixed(2)} · Mulai ${sst.started || '-'}${sst.open ? ` · <strong style="color:#e3b341">OPEN LONG @ $${sst.open.entry.toLocaleString()}</strong>` : ' · flat'}`;
      document.getElementById('paperst-trades').innerHTML = sn
        ? `<table style="width:100%;border-collapse:collapse;font-size:12px"><tr style="color:#8b949e"><th align="left">Masuk</th><th align="right">Entry</th><th align="right">Exit</th><th align="right">PnL</th><th align="right">R</th><th>Keluar</th></tr>` +
          str.slice(-5).reverse().map(t => `<tr><td>${t.entry_tgl}</td><td align="right">$${t.entry.toLocaleString()}</td><td align="right">$${t.exit.toLocaleString()}</td><td align="right" style="color:${t.pnl > 0 ? '#3fb950' : '#f85149'}">${t.pnl > 0 ? '+' : ''}${t.pnl}</td><td align="right">${t.r}</td><td>${t.alasan}</td></tr>`).join('') + `</table>`
        : 'Belum ada trade (menunggu flip-up pertama).';
    } else {
      document.getElementById('paperst-stats').textContent = 'paper-st belum pernah jalan.';
    }
  } catch(e) { document.getElementById('paperst-stats').textContent = 'Gagal muat paper-st.'; }
  const list = document.getElementById('news-list');
  list.innerHTML = '';
  let shown = 0;
  const renderBatch = (n) => {
    news.slice(shown, shown + n).forEach(a => {
      list.innerHTML += `
        <div class="article">
          <div class="source">${a.source} | ${(a.published || '').slice(0, 16)}</div>
          <div class="title"><a href="${a.link}" target="_blank">${a.title}</a> ${a.fear ? '<span class="badge neg">FEAR</span>' : ''}</div>
          <div class="coins"><span class="badge ${a.compound < -0.05 ? 'neg' : (a.compound > 0.05 ? 'pos' : 'neu')}">${a.compound}</span></div>
          ${a.summary ? '<div class="summary">' + a.summary.slice(0, 200) + '</div>' : ''}
        </div>`;
    });
    shown += n;
    document.getElementById('news-more').textContent =
      shown >= news.length ? '' : '⏳ scroll untuk berita lama (' + shown + '/' + news.length + ')';
  };
  renderBatch(10);
  if (window._newsObs) window._newsObs.disconnect();
  window._newsObs = new IntersectionObserver((es) => {
    if (es[0].isIntersecting && shown < news.length) renderBatch(15);
  });
  window._newsObs.observe(document.getElementById('news-more'));
}
load();
</script>
</body>
</html>"""

STATIC = os.path.join(os.path.dirname(__file__), "static")


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())
        else:
            super().do_GET()


def main():
    import shutil
    os.makedirs(os.path.join(STATIC, "data"), exist_ok=True)
    with open(os.path.join(STATIC, "index.html"), "w",
              encoding="utf-8") as f:
        f.write(HTML)
    for fn in ("latest.json", "gold_sentiment.json"):
        src = os.path.join(DATA_DIR, fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(STATIC, "data", fn))
    os.chdir(os.path.dirname(__file__))
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Emas dashboard: http://localhost:{PORT} (Ctrl+C berhenti)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
