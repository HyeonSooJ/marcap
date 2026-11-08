/* KIS Trader - 프론트엔드 (Vanilla JS) */
(() => {
  "use strict";

  // ------------------------------------------------------------------ 유틸
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const fmt = (n) => (n === null || n === undefined || Number.isNaN(n) ? "-" : Math.round(n).toLocaleString("ko-KR"));
  const fmtRate = (r) => `${r > 0 ? "+" : ""}${Number(r).toFixed(2)}%`;
  const signCls = (s) => (s > 0 ? "up" : s < 0 ? "down" : "");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const toNum = (v) => parseInt(String(v).replace(/[^\d]/g, ""), 10) || 0;
  const fmtTime = (t) => (t && t.length >= 6 ? `${t.slice(0, 2)}:${t.slice(2, 4)}:${t.slice(4, 6)}` : t || "");
  const fmtBig = (n) => {
    if (!n) return "-";
    if (n >= 1e12) return `${(n / 1e12).toFixed(1)}조`;
    if (n >= 1e8) return `${Math.round(n / 1e8).toLocaleString("ko-KR")}억`;
    if (n >= 1e4) return `${Math.round(n / 1e4).toLocaleString("ko-KR")}만`;
    return fmt(n);
  };
  // KRX 호가가격단위
  const tickSize = (p) => (p < 2000 ? 1 : p < 5000 ? 5 : p < 20000 ? 10 : p < 50000 ? 50 : p < 200000 ? 100 : p < 500000 ? 500 : 1000);
  const roundTick = (p) => { const t = tickSize(p); return Math.round(p / t) * t; };

  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* 저장 불가 환경 무시 */ } },
  };

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch { /* 빈 응답 */ }
    if (!res.ok) {
      let msg = data && data.detail;
      if (Array.isArray(msg)) msg = msg.map((d) => String(d.msg || d).replace(/^Value error, /, "")).join(", ");
      throw new Error(msg || `요청 실패 (HTTP ${res.status})`);
    }
    return data;
  }

  function toast(msg, type = "") {
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = msg;
    $("#toasts").appendChild(el);
    setTimeout(() => el.remove(), type === "error" ? 6000 : 3500);
  }

  // ------------------------------------------------------------------ 상태
  const state = {
    code: store.get("lastCode", "005930"),
    quote: null,
    book: null,
    side: "buy",
    ordType: "00",
    period: "D",
    chart: [],
    buyable: null,
    holdings: [],
    watch: store.get("watchlist", ["005930", "000660", "035420", "005380", "035720"]),
    watchQuotes: {},
    accTab: "balance",
    priceTouched: false,
  };

  // ------------------------------------------------------------------ 테마
  const savedTheme = store.get("theme", null);
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;
  $("#themeToggle").addEventListener("click", () => {
    const dark = getComputedStyle(document.documentElement).colorScheme === "dark";
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    store.set("theme", next);
    drawChart();
  });

  // ------------------------------------------------------------------ 상태 표시
  async function loadStatus() {
    try {
      const s = await api("/api/status");
      const b = $("#modeBadge");
      b.textContent = s.env_label;
      b.className = `badge ${s.env}`;
      $("#accountLabel").textContent = `계좌 ${s.account}`;
      if (s.env === "demo") toast("API 키가 없어 DEMO 모드로 실행 중입니다. 시세·주문은 가상입니다.");
      if (s.env === "prod") toast("실전투자 계좌에 연결되었습니다. 주문은 실제로 체결됩니다.", "error");
    } catch (e) {
      $("#modeBadge").textContent = "서버 연결 실패";
    }
  }

  // ------------------------------------------------------------------ 검색
  const searchInput = $("#searchInput");
  const searchResults = $("#searchResults");
  let searchTimer = null;
  let searchIdx = -1;

  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    const q = searchInput.value.trim();
    if (!q) { searchResults.hidden = true; return; }
    searchTimer = setTimeout(async () => {
      try {
        const items = await api(`/api/stocks/search?q=${encodeURIComponent(q)}`);
        searchIdx = items.length ? 0 : -1;
        searchResults.innerHTML = items.length
          ? items.map((s, i) => `<li role="option" data-code="${esc(s.code)}" class="${i === 0 ? "active" : ""}">
              <span><b>${esc(s.name)}</b> <span class="muted small">${esc(s.code)}</span></span>
              <span class="muted small">${esc(s.market)}</span></li>`).join("")
          : `<li class="muted">검색 결과가 없습니다. 6자리 코드를 입력 후 Enter</li>`;
        searchResults.hidden = false;
      } catch (e) { toast(e.message, "error"); }
    }, 150);
  });
  searchInput.addEventListener("keydown", (e) => {
    const items = $$("#searchResults li[data-code]");
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!items.length) return;
      searchIdx = (searchIdx + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      items.forEach((li, i) => li.classList.toggle("active", i === searchIdx));
      items[searchIdx].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      const q = searchInput.value.trim().toUpperCase();
      if (items[searchIdx]) pickSearch(items[searchIdx].dataset.code);
      else if (/^[0-9A-Z]{6}$/.test(q)) pickSearch(q);
    } else if (e.key === "Escape") {
      searchResults.hidden = true;
    }
  });
  searchResults.addEventListener("mousedown", (e) => {
    const li = e.target.closest("li[data-code]");
    if (li) { e.preventDefault(); pickSearch(li.dataset.code); }
  });
  searchInput.addEventListener("blur", () => setTimeout(() => (searchResults.hidden = true), 100));
  function pickSearch(code) {
    searchResults.hidden = true;
    searchInput.value = "";
    searchInput.blur();
    selectStock(code);
  }

  // ------------------------------------------------------------------ 종목 선택
  async function selectStock(code) {
    state.code = code;
    state.quote = null;
    state.book = null;
    state.priceTouched = false;
    store.set("lastCode", code);
    $("#qName").textContent = "불러오는 중…";
    $("#qCode").textContent = code;
    $("#priceInput").value = "";
    $("#qtyInput").value = "1";
    renderWatch();
    await refreshQuote(true);
    loadChart();
    refreshBuyable();
  }

  // ------------------------------------------------------------------ 현재가
  let lastPrice = null;
  async function refreshQuote(first = false) {
    const code = state.code;
    try {
      const [q, book] = await Promise.all([api(`/api/quote/${code}`), api(`/api/orderbook/${code}`)]);
      if (code !== state.code) return; // 그 사이 종목이 바뀜
      state.quote = q;
      state.book = book;
      renderQuote(q, first);
      renderBook(book);
      if (!state.priceTouched || !$("#priceInput").value) {
        $("#priceInput").value = fmt(q.price);
      }
      updateTotal();
      state.watchQuotes[code] = { price: q.price, rate: q.change_rate, sign: q.sign, name: q.name };
      renderWatch();
      updateLastCandle(q);
      $("#liveDot").classList.add("on");
    } catch (e) {
      $("#liveDot").classList.remove("on");
      if (first) {
        $("#qName").textContent = "조회 실패";
        toast(e.message, "error");
      }
    }
  }

  function renderQuote(q, first) {
    const cls = signCls(q.sign);
    $("#qName").textContent = q.name;
    $("#qCode").textContent = q.code;
    $("#qMarket").textContent = q.market || "";
    const priceEl = $("#qPrice");
    priceEl.textContent = fmt(q.price);
    priceEl.className = `big ${cls}`;
    if (!first && lastPrice !== null && lastPrice !== q.price) {
      priceEl.classList.add(q.price > lastPrice ? "flash-up" : "flash-down");
    }
    lastPrice = q.price;
    const arrow = q.sign > 0 ? "▲" : q.sign < 0 ? "▼" : "";
    $("#qChange").innerHTML = `<span class="${cls}">${arrow} ${fmt(q.change)} (${fmtRate(q.sign < 0 ? -Math.abs(q.change_rate) : q.change_rate)})</span>`;
    $("#qTime").textContent = `${q.time} 기준`;
    $("#watchToggle").classList.toggle("on", state.watch.includes(q.code));
    $("#watchToggle").textContent = state.watch.includes(q.code) ? "★" : "☆";

    const pc = (v) => `<span class="${signCls(v - q.base)}">${fmt(v)}</span>`;
    const stats = [
      ["시가", pc(q.open)], ["고가", pc(q.high)], ["저가", pc(q.low)], ["기준가", fmt(q.base)],
      ["상한가", `<span class="up">${fmt(q.upper)}</span>`], ["하한가", `<span class="down">${fmt(q.lower)}</span>`],
      ["거래량", fmt(q.volume)], ["거래대금", fmtBig(q.amount)],
    ];
    if (q.market_cap) stats.push(["시가총액", fmtBig(q.market_cap)]);
    if (q.per) stats.push(["PER", q.per.toFixed(2)]);
    if (q.pbr) stats.push(["PBR", q.pbr.toFixed(2)]);
    if (q.w52_high) stats.push(["52주 최고", fmt(q.w52_high)], ["52주 최저", fmt(q.w52_low)]);
    if (q.frgn_rate) stats.push(["외국인 소진율", `${q.frgn_rate.toFixed(2)}%`]);
    $("#qStats").innerHTML = stats.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");
    document.title = `${q.name} ${fmt(q.price)} (${fmtRate(q.sign < 0 ? -Math.abs(q.change_rate) : q.change_rate)}) - KIS Trader`;
  }

  // ------------------------------------------------------------------ 호가
  function renderBook(b) {
    const maxQ = Math.max(1, ...b.asks.map((a) => a.qty), ...b.bids.map((x) => x.qty));
    const base = b.base || (state.quote && state.quote.base) || 0;
    const rate = (p) => (base && p ? ((p - base) / base) * 100 : 0);
    const priceCell = (p) => `<td class="price ${signCls(p - base)}" data-price="${p}">${p ? fmt(p) : ""}
        ${p ? `<div class="small muted">${fmtRate(rate(p))}</div>` : ""}</td>`;
    const cur = b.price;
    let html = "";
    for (let i = b.asks.length - 1; i >= 0; i--) {
      const a = b.asks[i];
      html += `<tr class="ask ${a.price === cur ? "current" : ""}"><td class="qty l" style="--w:${(a.qty / maxQ) * 100}%">${a.qty ? fmt(a.qty) : ""}</td>${priceCell(a.price)}<td class="qty"></td></tr>`;
    }
    for (const x of b.bids) {
      html += `<tr class="bid ${x.price === cur ? "current" : ""}"><td class="qty"></td>${priceCell(x.price)}<td class="qty r" style="--w:${(x.qty / maxQ) * 100}%">${x.qty ? fmt(x.qty) : ""}</td></tr>`;
    }
    html += `<tr class="total"><td class="r">${fmt(b.total_ask)}</td><td style="text-align:center">총잔량</td><td>${fmt(b.total_bid)}</td></tr>`;
    $("#orderbook").innerHTML = html;
    $("#bookTime").textContent = fmtTime(b.time);
  }
  $("#orderbook").addEventListener("click", (e) => {
    const td = e.target.closest("td.price");
    if (!td || !Number(td.dataset.price)) return;
    setOrdType("00");
    $("#priceInput").value = fmt(Number(td.dataset.price));
    state.priceTouched = true;
    updateTotal();
    refreshBuyable();
  });

  // ------------------------------------------------------------------ 차트 (Canvas)
  const canvas = $("#chart");
  const tip = $("#chartTip");
  let chartGeom = null;

  async function loadChart() {
    const code = state.code;
    try {
      const rows = await api(`/api/chart/${code}?period=${state.period}`);
      if (code !== state.code) return;
      state.chart = rows;
      drawChart();
    } catch (e) {
      state.chart = [];
      drawChart();
      toast(`차트 조회 실패: ${e.message}`, "error");
    }
  }
  $("#periodSeg").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-period]");
    if (!b) return;
    $$("#periodSeg button").forEach((x) => x.classList.toggle("active", x === b));
    state.period = b.dataset.period;
    loadChart();
  });

  function updateLastCandle(q) {
    if (state.period !== "D" || !state.chart.length) return;
    const last = state.chart[state.chart.length - 1];
    const today = new Date();
    const ymd = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, "0")}${String(today.getDate()).padStart(2, "0")}`;
    if (last.date === ymd) {
      last.close = q.price;
      last.high = Math.max(last.high, q.price);
      last.low = Math.min(last.low, q.price);
      last.volume = q.volume || last.volume;
      drawChart();
    }
  }

  function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  function sma(rows, n) {
    const out = [];
    let sum = 0;
    rows.forEach((r, i) => {
      sum += r.close;
      if (i >= n) sum -= rows[i - n].close;
      out.push(i >= n - 1 ? sum / n : null);
    });
    return out;
  }

  function drawChart(hoverIdx = null) {
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.clientWidth, H = canvas.clientHeight;
    if (!W || !H) return;
    canvas.width = W * dpr; canvas.height = H * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const rows = state.chart;
    const C = { up: cssVar("--up"), down: cssVar("--down"), line: cssVar("--line"), muted: cssVar("--muted"), text: cssVar("--text") };
    ctx.font = "11px system-ui, sans-serif";
    if (!rows.length) {
      ctx.fillStyle = C.muted; ctx.textAlign = "center";
      ctx.fillText("차트 데이터가 없습니다", W / 2, H / 2);
      chartGeom = null;
      return;
    }
    const padR = 64, padT = 10, volH = Math.round(H * 0.2), gap = 14, padB = 20;
    const priceH = H - volH - gap - padT - padB;
    const plotW = W - padR - 4;
    const n = rows.length;
    const step = plotW / n;
    const bodyW = Math.max(1, Math.min(12, step * 0.7));
    const hi = Math.max(...rows.map((r) => r.high)), lo = Math.min(...rows.map((r) => r.low));
    const range = hi - lo || 1;
    const yP = (p) => padT + ((hi - p) / range) * priceH;
    const maxV = Math.max(1, ...rows.map((r) => r.volume));
    const volTop = padT + priceH + gap;
    const yV = (v) => volTop + volH - (v / maxV) * volH;
    const xAt = (i) => 4 + step * i + step / 2;

    // 가격 그리드
    ctx.strokeStyle = C.line; ctx.lineWidth = 1; ctx.fillStyle = C.muted; ctx.textAlign = "left";
    for (let k = 0; k <= 4; k++) {
      const p = lo + (range * k) / 4;
      const y = Math.round(yP(p)) + 0.5;
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(plotW + 4, y); ctx.stroke();
      ctx.fillText(fmt(p), plotW + 8, y + 4);
    }
    ctx.beginPath(); ctx.moveTo(0, volTop + volH + 0.5); ctx.lineTo(plotW + 4, volTop + volH + 0.5); ctx.stroke();

    // 날짜 라벨
    const labelEvery = Math.ceil(n / Math.max(2, Math.floor(plotW / 80)));
    ctx.textAlign = "center";
    rows.forEach((r, i) => {
      if (i % labelEvery === 0) {
        const d = r.date;
        const label = state.period === "D" || state.period === "W" ? `${d.slice(2, 4)}.${d.slice(4, 6)}.${d.slice(6, 8)}` : `${d.slice(0, 4)}.${d.slice(4, 6)}`;
        ctx.fillText(label, xAt(i), H - 5);
      }
    });

    // 캔들 + 거래량
    rows.forEach((r, i) => {
      const x = xAt(i);
      const up = r.close >= r.open;
      const col = up ? C.up : C.down;
      ctx.strokeStyle = col; ctx.fillStyle = col;
      ctx.beginPath(); ctx.moveTo(Math.round(x) + 0.5, yP(r.high)); ctx.lineTo(Math.round(x) + 0.5, yP(r.low)); ctx.stroke();
      const y1 = yP(Math.max(r.open, r.close)), y2 = yP(Math.min(r.open, r.close));
      ctx.fillRect(x - bodyW / 2, y1, bodyW, Math.max(1, y2 - y1));
      ctx.globalAlpha = 0.45;
      ctx.fillRect(x - bodyW / 2, yV(r.volume), bodyW, volTop + volH - yV(r.volume));
      ctx.globalAlpha = 1;
    });

    // 이동평균선
    [[5, "#f59f00"], [20, "#12b886"], [60, "#ae3ec9"]].forEach(([len, color]) => {
      const ma = sma(rows, len);
      ctx.strokeStyle = color; ctx.lineWidth = 1.2; ctx.beginPath();
      let started = false;
      ma.forEach((v, i) => {
        if (v === null) return;
        const x = xAt(i), y = yP(v);
        if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
      });
      ctx.stroke();
    });
    ctx.lineWidth = 1;

    // 현재가 라인
    const last = rows[n - 1];
    const yl = Math.round(yP(last.close)) + 0.5;
    ctx.setLineDash([3, 3]); ctx.strokeStyle = C.muted;
    ctx.beginPath(); ctx.moveTo(0, yl); ctx.lineTo(plotW + 4, yl); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = last.close >= last.open ? C.up : C.down;
    ctx.fillRect(plotW + 4, yl - 9, padR - 4, 18);
    ctx.fillStyle = "#fff"; ctx.textAlign = "left";
    ctx.fillText(fmt(last.close), plotW + 8, yl + 4);

    // 범례
    ctx.textAlign = "left";
    [["MA5", "#f59f00"], ["MA20", "#12b886"], ["MA60", "#ae3ec9"]].forEach(([t, c], k) => {
      ctx.fillStyle = c; ctx.fillText(t, plotW - 130 + k * 44, padT + 10);
    });

    // 크로스헤어
    if (hoverIdx !== null && rows[hoverIdx]) {
      const x = Math.round(xAt(hoverIdx)) + 0.5;
      ctx.strokeStyle = C.muted; ctx.setLineDash([2, 3]);
      ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, volTop + volH); ctx.stroke(); ctx.setLineDash([]);
    }
    chartGeom = { step, n };
  }

  canvas.addEventListener("mousemove", (e) => {
    if (!chartGeom) return;
    const rect = canvas.getBoundingClientRect();
    const i = Math.min(chartGeom.n - 1, Math.max(0, Math.floor((e.clientX - rect.left - 4) / chartGeom.step)));
    const r = state.chart[i];
    drawChart(i);
    const d = r.date;
    const cls = r.close >= r.open ? "up" : "down";
    tip.innerHTML = `<b>${d.slice(0, 4)}.${d.slice(4, 6)}.${d.slice(6, 8)}</b>
      &nbsp;시 ${fmt(r.open)} 고 ${fmt(r.high)} 저 ${fmt(r.low)} 종 <span class="${cls}">${fmt(r.close)}</span>
      &nbsp;거래량 ${fmt(r.volume)}`;
    tip.hidden = false;
  });
  canvas.addEventListener("mouseleave", () => { tip.hidden = true; drawChart(); });
  window.addEventListener("resize", () => drawChart());

  // ------------------------------------------------------------------ 관심종목 / 거래량 순위
  function renderWatch() {
    const ul = $("#watchList");
    if (!state.watch.length) {
      ul.innerHTML = `<li class="empty">☆ 버튼으로 관심종목을 추가하세요</li>`;
      return;
    }
    ul.innerHTML = state.watch.map((code) => {
      const q = state.watchQuotes[code] || {};
      const rate = q.sign < 0 ? -Math.abs(q.rate) : q.rate;
      return `<li data-code="${esc(code)}" class="${code === state.code ? "selected" : ""}">
        <span class="nm">${esc(q.name || code)}</span><span class="px ${signCls(q.sign)}">${q.price ? fmt(q.price) : "-"}</span>
        <span class="cd">${esc(code)}</span><span class="rt ${signCls(q.sign)}">${q.price ? fmtRate(rate) : ""}</span></li>`;
    }).join("");
  }
  async function refreshWatchQuotes() {
    for (const code of state.watch) {
      if (code === state.code || document.hidden) continue;
      try {
        const q = await api(`/api/quote/${code}`);
        state.watchQuotes[code] = { price: q.price, rate: q.change_rate, sign: q.sign, name: q.name };
      } catch { /* 개별 실패 무시 */ }
    }
    renderWatch();
  }
  $("#watchToggle").addEventListener("click", () => {
    const code = state.code;
    const i = state.watch.indexOf(code);
    if (i >= 0) state.watch.splice(i, 1); else state.watch.unshift(code);
    store.set("watchlist", state.watch);
    const on = state.watch.includes(code);
    $("#watchToggle").classList.toggle("on", on);
    $("#watchToggle").textContent = on ? "★" : "☆";
    renderWatch();
  });

  async function loadRank() {
    const ul = $("#rankList");
    ul.innerHTML = `<li class="empty">불러오는 중…</li>`;
    try {
      const rows = await api("/api/ranking/volume");
      ul.innerHTML = rows.map((r) => {
        const rate = r.sign < 0 ? -Math.abs(r.change_rate) : r.change_rate;
        return `<li data-code="${esc(r.code)}">
          <span class="nm">${r.rank}. ${esc(r.name)}</span><span class="px ${signCls(r.sign)}">${fmt(r.price)}</span>
          <span class="cd">거래량 ${fmtBig(r.volume)}</span><span class="rt ${signCls(r.sign)}">${fmtRate(rate)}</span></li>`;
      }).join("") || `<li class="empty">데이터 없음</li>`;
    } catch (e) {
      ul.innerHTML = `<li class="empty">${esc(e.message)}</li>`;
    }
  }
  $$("[data-side-tab]").forEach((b) => b.addEventListener("click", () => {
    $$("[data-side-tab]").forEach((x) => x.classList.toggle("active", x === b));
    const rank = b.dataset.sideTab === "rank";
    $("#watchList").hidden = rank;
    $("#rankList").hidden = !rank;
    if (rank) loadRank();
  }));
  [$("#watchList"), $("#rankList")].forEach((ul) => ul.addEventListener("click", (e) => {
    const li = e.target.closest("li[data-code]");
    if (li) selectStock(li.dataset.code);
  }));

  // ------------------------------------------------------------------ 주문 폼
  const priceInput = $("#priceInput"), qtyInput = $("#qtyInput");

  function setSide(side) {
    state.side = side;
    $$(".otab").forEach((b) => b.classList.toggle("active", b.dataset.side === side));
    const btn = $("#submitOrder");
    btn.className = `submit ${side}`;
    btn.textContent = side === "buy" ? "매수" : "매도";
    refreshBuyable();
  }
  function setOrdType(t) {
    state.ordType = t;
    $$("#ordTypeSeg button").forEach((b) => b.classList.toggle("active", b.dataset.type === t));
    priceInput.disabled = t === "01";
    $$('[data-step="price"]').forEach((b) => (b.disabled = t === "01"));
    if (t === "01") priceInput.value = "시장가";
    else if (state.quote) priceInput.value = fmt(state.quote.price);
    updateTotal();
  }
  $$(".otab").forEach((b) => b.addEventListener("click", () => setSide(b.dataset.side)));
  $("#ordTypeSeg").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-type]");
    if (b) { setOrdType(b.dataset.type); refreshBuyable(); }
  });

  function curPrice() {
    if (state.ordType === "01") return state.quote ? state.quote.price : 0;
    return toNum(priceInput.value);
  }
  function updateTotal() {
    const total = curPrice() * toNum(qtyInput.value);
    $("#totalValue").textContent = `${fmt(total)}원${state.ordType === "01" ? " (예상)" : ""}`;
  }

  $$("[data-step]").forEach((b) => b.addEventListener("click", () => {
    const dir = Number(b.dataset.dir);
    if (b.dataset.step === "price") {
      let p = toNum(priceInput.value) || (state.quote ? state.quote.price : 0);
      p = dir > 0 ? p + tickSize(p) : p - tickSize(p - 1);
      if (state.quote) p = Math.min(state.quote.upper || p, Math.max(state.quote.lower || p, p));
      priceInput.value = fmt(Math.max(1, p));
      state.priceTouched = true;
    } else {
      qtyInput.value = fmt(Math.max(1, toNum(qtyInput.value) + dir));
    }
    updateTotal();
  }));
  priceInput.addEventListener("input", () => {
    state.priceTouched = true;
    const n = toNum(priceInput.value);
    priceInput.value = n ? fmt(n) : "";
    updateTotal();
  });
  priceInput.addEventListener("change", () => {
    const n = toNum(priceInput.value);
    if (n) priceInput.value = fmt(roundTick(n));
    updateTotal();
    refreshBuyable();
  });
  qtyInput.addEventListener("input", () => {
    const n = toNum(qtyInput.value);
    qtyInput.value = n ? fmt(n) : "";
    updateTotal();
  });

  $$("[data-pct]").forEach((b) => b.addEventListener("click", async () => {
    const pct = Number(b.dataset.pct) / 100;
    let max = 0;
    if (state.side === "buy") {
      await refreshBuyable();
      max = state.buyable ? state.buyable.max_qty : 0;
    } else {
      const h = state.holdings.find((x) => x.code === state.code);
      max = h ? h.sellable_qty : 0;
    }
    qtyInput.value = fmt(Math.max(pct === 1 ? max : Math.floor(max * pct), 0));
    updateTotal();
  }));

  let buyableTimer = null;
  function refreshBuyable() {
    clearTimeout(buyableTimer);
    return new Promise((resolve) => {
      buyableTimer = setTimeout(async () => {
        const code = state.code;
        if (state.side === "buy") {
          $("#availLabel").textContent = "주문가능금액";
          $("#maxLabel").textContent = "최대 매수가능";
          const price = curPrice();
          if (state.ordType === "00" && !price) { resolve(); return; }
          try {
            const r = await api(`/api/buyable/${code}?price=${price}&ord_dvsn=${state.ordType}`);
            if (code !== state.code) return resolve();
            state.buyable = r;
            $("#availValue").textContent = `${fmt(r.cash)}원`;
            $("#maxValue").textContent = `${fmt(r.max_qty)}주`;
          } catch (e) {
            state.buyable = null;
            $("#availValue").textContent = "-";
            $("#maxValue").textContent = "-";
          }
        } else {
          $("#availLabel").textContent = "보유수량";
          $("#maxLabel").textContent = "매도가능수량";
          if (!state.holdings.length) await loadBalance(true);
          const h = state.holdings.find((x) => x.code === state.code);
          $("#availValue").textContent = `${fmt(h ? h.qty : 0)}주`;
          $("#maxValue").textContent = `${fmt(h ? h.sellable_qty : 0)}주`;
        }
        resolve();
      }, 200);
    });
  }

  // 모달 (확인창)
  function confirmModal(title, html, okLabel = "확인", okClass = "") {
    const dlg = $("#modal");
    $("#modalTitle").textContent = title;
    $("#modalContent").innerHTML = html;
    const ok = $("#modalOk");
    ok.textContent = okLabel;
    ok.className = `primary ${okClass}`;
    dlg.returnValue = "";
    dlg.showModal();
    const input = dlg.querySelector("#modalContent input");
    if (input) { input.focus(); input.select(); } else ok.focus();
    return new Promise((resolve) => {
      dlg.addEventListener("close", () => resolve(dlg.returnValue === "ok" ? (input ? input.value : true) : null), { once: true });
    });
  }

  $("#orderForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = state.quote;
    if (!q) { toast("시세를 불러온 후 주문하세요.", "error"); return; }
    const qty = toNum(qtyInput.value);
    const price = state.ordType === "00" ? toNum(priceInput.value) : 0;
    if (qty <= 0) { toast("수량을 입력하세요.", "error"); return; }
    if (state.ordType === "00") {
      if (!price) { toast("가격을 입력하세요.", "error"); return; }
      if (price % tickSize(price)) { toast(`호가단위(${fmt(tickSize(price))}원)에 맞지 않는 가격입니다.`, "error"); return; }
      if ((q.upper && price > q.upper) || (q.lower && price < q.lower)) {
        toast(`가격제한폭(${fmt(q.lower)} ~ ${fmt(q.upper)}) 밖의 가격입니다.`, "error"); return;
      }
    }
    const sideLabel = state.side === "buy" ? "매수" : "매도";
    const env = $("#modeBadge").textContent;
    const ok = await confirmModal(`${sideLabel} 주문 확인`, `
      <dl>
        <dt>종목</dt><dd>${esc(q.name)} (${esc(q.code)})</dd>
        <dt>구분</dt><dd class="${state.side === "buy" ? "up" : "down"}">${sideLabel}</dd>
        <dt>주문유형</dt><dd>${state.ordType === "00" ? "지정가" : "시장가"}</dd>
        <dt>가격</dt><dd>${state.ordType === "00" ? `${fmt(price)}원` : "시장가"}</dd>
        <dt>수량</dt><dd>${fmt(qty)}주</dd>
        <dt>주문금액</dt><dd>${fmt((price || q.price) * qty)}원${state.ordType === "01" ? " (예상)" : ""}</dd>
      </dl>
      <p class="warn">[${esc(env)}] 확인을 누르면 주문이 전송됩니다.</p>`, `${sideLabel} 주문`, state.side);
    if (!ok) return;

    const btn = $("#submitOrder");
    btn.disabled = true;
    try {
      const r = await api("/api/order", { method: "POST", body: { side: state.side, code: q.code, qty, price, ord_dvsn: state.ordType } });
      toast(`${sideLabel} 주문 접수 · 주문번호 ${r.order_no} ${r.message ? `· ${r.message}` : ""}`, "ok");
      setTimeout(() => { loadBalance(); loadOrders(); refreshBuyable(); }, 600);
    } catch (err) {
      toast(`주문 실패: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
    }
  });

  // ------------------------------------------------------------------ 잔고 / 주문내역
  async function loadBalance(silent = false) {
    try {
      const b = await api("/api/balance");
      state.holdings = b.holdings;
      const s = b.summary;
      const card = (k, v, cls = "") => `<div class="card"><div class="k">${k}</div><div class="v ${cls}">${v}</div></div>`;
      $("#balanceSummary").innerHTML =
        card("총 평가금액", `${fmt(s.total_eval)}원`) +
        card("예수금", `${fmt(s.deposit)}원`) +
        card("D+2 예수금", `${fmt(s.d2_deposit)}원`) +
        card("주식 평가금액", `${fmt(s.stock_eval)}원`) +
        card("평가손익", `${s.pnl > 0 ? "+" : ""}${fmt(s.pnl)}원`, signCls(s.pnl)) +
        card("수익률", fmtRate(s.pnl_rate), signCls(s.pnl_rate));
      $("#holdingsBody").innerHTML = b.holdings.length ? b.holdings.map((h) => `
        <tr class="link" data-code="${esc(h.code)}">
          <td><b>${esc(h.name)}</b> <span class="muted small">${esc(h.code)}</span></td>
          <td class="r">${fmt(h.qty)}</td><td class="r">${fmt(h.sellable_qty)}</td>
          <td class="r">${fmt(h.avg_price)}</td><td class="r">${fmt(h.price)}</td>
          <td class="r">${fmt(h.eval_amount)}</td>
          <td class="r ${signCls(h.pnl)}">${h.pnl > 0 ? "+" : ""}${fmt(h.pnl)}</td>
          <td class="r ${signCls(h.pnl_rate)}">${fmtRate(h.pnl_rate)}</td>
        </tr>`).join("") : `<tr><td colspan="8" class="empty">보유 종목이 없습니다</td></tr>`;
      if (state.side === "sell") refreshBuyable();
    } catch (e) {
      if (!silent) toast(`잔고 조회 실패: ${e.message}`, "error");
      $("#holdingsBody").innerHTML = `<tr><td colspan="8" class="empty">${esc(e.message)}</td></tr>`;
    }
  }

  async function loadOrders() {
    try {
      const rows = await api("/api/orders");
      $("#ordersBody").innerHTML = rows.length ? rows.map((o) => {
        const status = o.cancelled ? "취소" : o.remain_qty === 0 && o.filled_qty > 0 ? "체결" : o.filled_qty > 0 ? "부분체결" : o.remain_qty > 0 ? "미체결" : "-";
        return `<tr>
          <td>${fmtTime(o.time)}</td>
          <td class="link" data-code="${esc(o.code)}"><b>${esc(o.name)}</b></td>
          <td><span class="tag ${o.side}">${o.side === "buy" ? "매수" : "매도"}</span></td>
          <td>${esc(o.type)}</td>
          <td class="r">${o.price ? fmt(o.price) : "시장가"}</td>
          <td class="r">${fmt(o.qty)}</td><td class="r">${fmt(o.filled_qty)}</td>
          <td class="r">${o.avg_price ? fmt(o.avg_price) : "-"}</td><td class="r">${fmt(o.remain_qty)}</td>
          <td>${status}</td>
          <td>${o.cancellable ? `<div class="act">
              <button class="ghost" data-amend="${esc(o.order_no)}" data-org="${esc(o.org_no)}" data-price="${o.price}">정정</button>
              <button class="ghost" data-cancel="${esc(o.order_no)}" data-org="${esc(o.org_no)}">취소</button></div>` : ""}</td>
        </tr>`;
      }).join("") : `<tr><td colspan="11" class="empty">오늘 주문 내역이 없습니다</td></tr>`;
    } catch (e) {
      $("#ordersBody").innerHTML = `<tr><td colspan="11" class="empty">${esc(e.message)}</td></tr>`;
    }
  }

  $("#ordersBody").addEventListener("click", async (e) => {
    const link = e.target.closest("[data-code]");
    const cancel = e.target.closest("[data-cancel]");
    const amend = e.target.closest("[data-amend]");
    if (cancel) {
      const ok = await confirmModal("주문 취소", `<p>주문번호 <b>${esc(cancel.dataset.cancel)}</b> 의 미체결 잔량을 전부 취소합니다.</p>`, "주문 취소");
      if (!ok) return;
      try {
        const r = await api("/api/order/revise", { method: "POST", body: { org_no: cancel.dataset.org, order_no: cancel.dataset.cancel, action: "cancel" } });
        toast(r.message || "취소 주문 완료", "ok");
      } catch (err) { toast(`취소 실패: ${err.message}`, "error"); }
      setTimeout(() => { loadOrders(); loadBalance(true); }, 500);
    } else if (amend) {
      const v = await confirmModal("가격 정정", `<p>주문번호 <b>${esc(amend.dataset.amend)}</b> 의 미체결 잔량 전부를 새 지정가로 정정합니다.</p>
        <input id="amendPrice" inputmode="numeric" value="${fmt(Number(amend.dataset.price) || (state.quote ? state.quote.price : 0))}">`, "정정");
      if (v === null) return;
      const price = toNum(v);
      if (!price || price % tickSize(price)) { toast("호가단위에 맞는 가격을 입력하세요.", "error"); return; }
      try {
        const r = await api("/api/order/revise", { method: "POST", body: { org_no: amend.dataset.org, order_no: amend.dataset.amend, action: "amend", price } });
        toast(r.message || "정정 주문 완료", "ok");
      } catch (err) { toast(`정정 실패: ${err.message}`, "error"); }
      setTimeout(() => { loadOrders(); loadBalance(true); }, 500);
    } else if (link) {
      selectStock(link.dataset.code);
    }
  });
  $("#holdingsBody").addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-code]");
    if (tr) { selectStock(tr.dataset.code); setSide("sell"); }
  });

  $$("[data-acc-tab]").forEach((b) => b.addEventListener("click", () => {
    $$("[data-acc-tab]").forEach((x) => x.classList.toggle("active", x === b));
    state.accTab = b.dataset.accTab;
    $("#balanceView").hidden = state.accTab !== "balance";
    $("#ordersView").hidden = state.accTab !== "orders";
    state.accTab === "balance" ? loadBalance() : loadOrders();
  }));
  $("#refreshAccount").addEventListener("click", () => (state.accTab === "balance" ? loadBalance() : loadOrders()));

  // ------------------------------------------------------------------ 폴링
  let polling = false;
  setInterval(async () => {
    if (document.hidden || polling) return;
    polling = true;
    try { await refreshQuote(); } finally { polling = false; }
  }, 3000);
  setInterval(() => {
    if (document.hidden) return;
    state.accTab === "balance" ? loadBalance(true) : loadOrders();
  }, 15000);
  setInterval(refreshWatchQuotes, 20000);

  // ------------------------------------------------------------------ 시작
  loadStatus();
  renderWatch();
  selectStock(state.code);
  loadBalance(true);
  setTimeout(refreshWatchQuotes, 1500);
})();
