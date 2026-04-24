let tvWidget = null;
let btLwChart = null;

// ── 차트 높이 드래그 조절 ──────────────────────────────────
(function initChartResize() {
  const MIN_H = 200, MAX_H = 900;
  document.querySelectorAll(".chart-resize-handle").forEach(handle => {
    let startY = 0, startH = 0, target = null;

    handle.addEventListener("mousedown", e => {
      target = document.getElementById(handle.dataset.target);
      if (!target) return;
      startY = e.clientY;
      startH = target.offsetHeight;
      document.body.style.userSelect = "none";
      document.body.style.cursor = "ns-resize";
      e.preventDefault();
    });

    document.addEventListener("mousemove", e => {
      if (!target) return;
      const newH = Math.min(MAX_H, Math.max(MIN_H, startH + (e.clientY - startY)));
      target.style.height = newH + "px";
    });

    document.addEventListener("mouseup", () => {
      target = null;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    });
  });
})();

// ── 마켓 목록 로드 ──────────────────────────────────────
async function loadMarkets() {
  try {
    const res = await fetch("/api/markets");
    if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) throw new Error("마켓 목록이 비어있습니다");
    const sel = document.getElementById("marketSelect");
    sel.innerHTML = "";
    data.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m.market;
      opt.textContent = `${m.market} (${m.korean_name})`;
      sel.appendChild(opt);
    });
    sel.value = "KRW-BTC";
    loadTvChart();
  } catch (e) {
    showToast("마켓 목록 로드 실패: " + e.message);
  }
}

// ── 티커 업데이트 ───────────────────────────────────────
async function loadTicker(market) {
  try {
    const res = await fetch(`/api/ticker?market=${market}`);
    if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
    const json = await res.json();
    const t = Array.isArray(json) ? json[0] : null;
    if (!t) throw new Error("응답 데이터 없음");

    const fmt  = n => Number(n).toLocaleString("ko-KR");
    const fmtB = n => (n / 1e8).toFixed(1) + "억";

    document.getElementById("t-price").textContent  = fmt(t.trade_price) + " ₩";
    document.getElementById("t-change").textContent = (t.signed_change_price >= 0 ? "+" : "") + fmt(t.signed_change_price) + " ₩";
    document.getElementById("t-rate").textContent   = (t.signed_change_rate >= 0 ? "+" : "") + (t.signed_change_rate * 100).toFixed(2) + "%";
    document.getElementById("t-vol").textContent    = fmtB(t.acc_trade_price_24h);
    document.getElementById("t-high52").textContent = fmt(t.highest_52_week_price) + " ₩";
    document.getElementById("t-low52").textContent  = fmt(t.lowest_52_week_price) + " ₩";

    const dir = t.change === "RISE" ? "up" : t.change === "FALL" ? "down" : "neutral";
    document.getElementById("t-change").className = "value " + dir;
    document.getElementById("t-rate").className   = "value " + dir;
  } catch (e) {
    // 30초 주기 폴링이므로 toast 대신 콘솔만 기록 (화면 도배 방지)
    console.warn("티커 업데이트 실패:", e.message);
  }
}

// Upbit 마켓 코드 → TradingView 심볼 변환 (예: KRW-BTC → UPBIT:BTCKRW)
function toTvSymbol(market) {
  const [quote, base] = market.split("-");
  return `UPBIT:${base}${quote}`;
}

const TV_INTERVAL_MAP = {
  minutes5: "5", minutes15: "15", minutes60: "60", minutes240: "240",
  days: "D", weeks: "W", months: "M",
};

function createTvWidget(containerId, symbol, interval) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  const iframe = document.createElement("iframe");
  iframe.src = [
    "https://www.tradingview.com/widgetembed/?",
    `symbol=${encodeURIComponent(symbol)}`,
    `&interval=${TV_INTERVAL_MAP[interval] || "D"}`,
    "&theme=dark&style=1&locale=kr",
    "&toolbar_bg=%23161b22",
    "&enable_publishing=0&hide_top_toolbar=0&hide_legend=0&save_image=0",
    "&studies=RSI@tv-basicstudies%1FVolume@tv-basicstudies",
  ].join("");
  iframe.style.cssText = "width:100%;height:100%;border:none;display:block;";
  iframe.allowFullscreen = true;
  container.appendChild(iframe);
  return iframe;
}

// ── 차트 탭: TradingView 위젯 로드 ──────────────────────
async function loadTvChart() {
  const market   = document.getElementById("marketSelect").value;
  if (!market) return;
  const interval = document.getElementById("chartIntervalSelect").value;

  tvWidget = createTvWidget("tradingview-chart", toTvSymbol(market), interval);
  loadTicker(market);

  try {
    const res = await fetch(`/api/signals?market=${market}&count=1000&interval=${interval}`);
    const signalsData = await res.json();
    if (signalsData && !signalsData.error) renderSignalCards(signalsData);
  } catch (_) {}
}
