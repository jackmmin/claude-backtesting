let equityChart = null;
let tvWidget = null;
let tvBtWidget = null;

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
  const res = await fetch("/api/markets");
  const data = await res.json();
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
}

// ── 티커 업데이트 ───────────────────────────────────────
async function loadTicker(market) {
  const res = await fetch(`/api/ticker?market=${market}`);
  const [t] = await res.json();

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

const SIGNAL_COLORS = {
  K_VOLATILITY_BREAKOUT: "#3fb950",
  RSI_OVERSOLD_BOUNCE:   "#a371f7",
  MA_GOLDEN_CROSS:       "#79c0ff",
  BOLLINGER_BOUNCE:      "#fb8500",
};

function renderSignalCards(signalsData) {
  const container = document.getElementById("signalCardsContainer");
  const grid = document.getElementById("signalCardsGrid");
  if (!grid) return;
  grid.innerHTML = "";
  for (const sig of (signalsData.signals || [])) {
    const color = SIGNAL_COLORS[sig.strategy] || "#58a6ff";
    const card = document.createElement("div");
    card.style.cssText = `background:#161b22;border:1px solid ${sig.triggered ? color : "#30363d"};border-radius:10px;padding:16px 18px;`;
    card.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span style="font-weight:700;color:#e6edf3;font-size:0.9rem;">${sig.name}</span>
        <span style="padding:2px 9px;border-radius:20px;font-size:0.7rem;font-weight:700;
          background:${sig.triggered ? color : "#30363d"};color:${sig.triggered ? "#0d1117" : "#8b949e"};">
          ${sig.triggered ? "진입 신호" : "대기중"}
        </span>
      </div>
      <div style="font-size:0.8rem;color:#8b949e;line-height:1.7;">${getSignalMetrics(sig)}</div>`;
    grid.appendChild(card);
  }
  container.style.display = "block";
}

function getSignalMetrics(sig) {
  const fmt = n => Number(n).toLocaleString("ko-KR");
  const d = sig.details || {};
  if (sig.strategy === "K_VOLATILITY_BREAKOUT") {
    return `<div>목표가: <span style="color:#e6edf3;font-weight:600;">${fmt(d.target_price)} ₩</span></div>
            <div>현재가: <span style="color:#e6edf3;font-weight:600;">${fmt(d.current_price)} ₩</span></div>
            <div style="font-size:0.75rem;margin-top:2px;">K=${d.k} · 전봉범위=${fmt(d.prev_range)} ₩</div>`;
  }
  if (sig.strategy === "RSI_OVERSOLD_BOUNCE") {
    return `<div>RSI: <span style="color:#e6edf3;font-weight:600;">${d.rsi_value !== null ? d.rsi_value?.toFixed(1) : "-"}</span>
            <span style="font-size:0.75rem;"> (임계값 ${d.threshold})</span></div>
            <div style="font-size:0.75rem;margin-top:2px;">기간=${d.period}${d.period_label || "봉"}</div>`;
  }
  if (sig.strategy === "MA_GOLDEN_CROSS") {
    return `<div>MA5: <span style="color:#e6edf3;font-weight:600;">${d.ma5 !== null ? fmt(d.ma5) : "-"}</span></div>
            <div>MA20: <span style="color:#e6edf3;font-weight:600;">${d.ma20 !== null ? fmt(d.ma20) : "-"}</span></div>
            <div style="font-size:0.75rem;margin-top:2px;">${d.cross_candles_ago != null ? `${d.cross_candles_ago}봉 전 크로스` : "크로스 없음"}</div>`;
  }
  if (sig.strategy === "BOLLINGER_BOUNCE") {
    return `<div>현재가: <span style="color:#e6edf3;font-weight:600;">${d.current_price != null ? fmt(d.current_price) : "-"} ₩</span></div>
            <div>하단밴드: <span style="color:#e6edf3;font-weight:600;">${d.lower_band != null ? fmt(d.lower_band) : "-"} ₩</span></div>
            <div style="font-size:0.75rem;margin-top:2px;">중심=${d.middle_band != null ? fmt(d.middle_band) : "-"} ₩</div>`;
  }
  return "";
}

// ── 이벤트 바인딩 ───────────────────────────────────────
document.getElementById("marketSelect").addEventListener("change", () => {
  const activeTab = document.querySelector(".tab-pane.active").id;
  if (activeTab === "tab-chart") loadTvChart();
});

document.getElementById("chartIntervalSelect").addEventListener("change", loadTvChart);

// ── 토스트 알림 ─────────────────────────────────────────
let _toastTimer = null;
function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  if (_toastTimer) clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}

// ── 탭 전환 ────────────────────────────────────────────
let _keysAllSet = false;

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    if (btn.dataset.tab === "live-trading" && !_keysAllSet) {
      showToast("⚠ upbit_keys 파일에 API 키를 등록해주세요");
      return;
    }
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

// ── 백테스팅 ────────────────────────────────────────────
const STRATEGY_NAMES = {
  K_VOLATILITY_BREAKOUT: "K변동성 돌파",
  RSI_OVERSOLD_BOUNCE:   "RSI 과매도 반등",
  MA_GOLDEN_CROSS:       "MA 골든크로스",
  BOLLINGER_BOUNCE:      "볼린저밴드 반등",
};

function getStrategyDesc(strategy) {
  const g   = id => document.getElementById(id);
  const chk = id => g(id) ? g(id).checked : false;
  const val = id => g(id) ? g(id).value   : "";

  if (strategy === "K_VOLATILITY_BREAKOUT") {
    const k    = val("kSlider");
    const exit = [];
    if (chk("kUseTp")) exit.push(`TP+${val("kTp")}%`);
    if (chk("kUseSl")) exit.push(`SL-${val("kSl")}%`);
    if (!exit.length) exit.push("당일종가");
    const filter = [];
    if (chk("kMaFilter"))     filter.push(`MA${val("kMaPeriod")}봉`);
    if (chk("kVolumeFilter")) filter.push(`볼륨${val("kVolumeMult")}x`);
    return `진입: 시가+K(${k})×전봉변동폭 | 청산: ${exit.join(" · ")} | 필터: ${filter.length ? filter.join(" · ") : "없음"}`;
  }
  if (strategy === "RSI_OVERSOLD_BOUNCE") {
    const period = val("rsiPeriod"), thr = val("rsiThreshold");
    const mode   = val("rsiEntryMode") === "crossover" ? "회복후진입" : "즉시진입";
    const exit   = [];
    if (chk("rsiUseTp"))      exit.push(`TP+${val("rsiTp")}%`);
    if (chk("rsiUseSl"))      exit.push(`SL-${val("rsiSl")}%`);
    if (chk("rsiUseRsiExit")) exit.push(`RSI${val("rsiExit")}↑`);
    const maxBars = parseInt(val("rsiMaxHoldBars"));
    if (maxBars > 0) exit.push(`최대${maxBars}봉`);
    if (!exit.length) exit.push("수동청산");
    const filter = [];
    if (chk("rsiMaFilter"))     filter.push(`MA${val("rsiMaPeriod")}봉`);
    if (chk("rsiVolumeFilter")) filter.push(`볼륨${val("rsiVolumeMult")}x`);
    return `진입: RSI${period} <${thr} · ${mode} | 청산: ${exit.join(" · ")} | 필터: ${filter.length ? filter.join(" · ") : "없음"}`;
  }
  if (strategy === "MA_GOLDEN_CROSS") {
    const fast = val("maFast"), slow = val("maSlow");
    const exit = [];
    if (chk("maUseTp"))    exit.push(`TP+${val("maTp")}%`);
    if (chk("maUseSl"))    exit.push(`SL-${val("maSl")}%`);
    if (chk("mauseMAExit")) exit.push("데드크로스");
    const maxBars = parseInt(val("maMaxHoldBars"));
    if (maxBars > 0) exit.push(`최대${maxBars}봉`);
    if (!exit.length) exit.push("수동청산");
    const filter = [];
    if (chk("maVolumeFilter")) filter.push(`볼륨${val("maVolumeMult")}x`);
    return `진입: MA${fast}/MA${slow} 골든크로스 | 청산: ${exit.join(" · ")} | 필터: ${filter.length ? filter.join(" · ") : "없음"}`;
  }
  if (strategy === "BOLLINGER_BOUNCE") {
    const period = val("bbPeriod"), std = val("bbStd");
    const exit   = [];
    if (chk("bbUseTp"))         exit.push(`TP+${val("bbTp")}%`);
    if (chk("bbUseSl"))         exit.push(`SL-${val("bbSl")}%`);
    if (chk("bbUseMiddleExit")) exit.push("중간선청산");
    const maxBars = parseInt(val("bbMaxHoldBars"));
    if (maxBars > 0) exit.push(`최대${maxBars}봉`);
    if (!exit.length) exit.push("수동청산");
    const filter = [];
    if (chk("bbVolumeFilter")) filter.push(`볼륨${val("bbVolumeMult")}x`);
    return `진입: BB${period}봉 σ${std} | 청산: ${exit.join(" · ")} | 필터: ${filter.length ? filter.join(" · ") : "없음"}`;
  }
  return "";
}

function onStrategyChange() {
  const strategy = document.getElementById("strategySelect").value;
  ["ctrl-k", "ctrl-rsi", "ctrl-ma", "ctrl-bb"].forEach(id =>
    document.getElementById(id).classList.remove("active")
  );
  const map = {
    K_VOLATILITY_BREAKOUT: "ctrl-k",
    RSI_OVERSOLD_BOUNCE:   "ctrl-rsi",
    MA_GOLDEN_CROSS:       "ctrl-ma",
    BOLLINGER_BOUNCE:      "ctrl-bb",
  };
  const id = map[strategy];
  if (id) document.getElementById(id).classList.add("active");
  document.getElementById("strategyDesc").textContent = getStrategyDesc(strategy);
  document.getElementById("btResult").style.display = "none";
}

function updateStrategyDesc() {
  document.getElementById("strategyDesc").textContent =
    getStrategyDesc(document.getElementById("strategySelect").value);
}

document.querySelectorAll(".param-panel input, .param-panel select").forEach(el => {
  el.addEventListener("input",  updateStrategyDesc);
  el.addEventListener("change", updateStrategyDesc);
});

const kSlider  = document.getElementById("kSlider");
const kDisplay = document.getElementById("kValueDisplay");
kSlider.addEventListener("input", () => { kDisplay.textContent = kSlider.value; });

const capitalInput = document.getElementById("initialCapital");
capitalInput.addEventListener("input", () => {
  const raw    = capitalInput.value.replace(/[^0-9]/g, "");
  const cursor = capitalInput.selectionStart;
  const prevLen = capitalInput.value.length;
  capitalInput.value = raw ? Number(raw).toLocaleString("ko-KR") : "";
  const diff = capitalInput.value.length - prevLen;
  capitalInput.setSelectionRange(cursor + diff, cursor + diff);
});
function getCapitalValue() {
  return parseInt(capitalInput.value.replace(/[^0-9]/g, "")) || 1000000;
}

document.getElementById("btRunBtn").addEventListener("click", runBacktest);

const INTERVAL_LABEL = {
  minutes15: "15분봉", minutes60: "1시간봉", minutes240: "4시간봉",
  days: "1일봉", weeks: "주봉", months: "월봉",
};

async function runBacktest() {
  const market   = document.getElementById("marketSelect").value;
  if (!market) return;
  const strategy = document.getElementById("strategySelect").value;
  const interval = document.getElementById("intervalSelect").value;
  const count    = parseInt(document.getElementById("candleCount").value) || 200;
  const initialCapital = getCapitalValue();

  let params = `market=${market}&strategy=${strategy}&interval=${interval}&count=${count}&initial_capital=${initialCapital}`;
  if (strategy === "K_VOLATILITY_BREAKOUT") {
    params += `&k=${parseFloat(kSlider.value)}`;
    params += `&k_use_tp=${document.getElementById("kUseTp").checked}`;
    params += `&k_tp=${parseFloat(document.getElementById("kTp").value) / 100}`;
    params += `&k_use_sl=${document.getElementById("kUseSl").checked}`;
    params += `&k_sl=${-parseFloat(document.getElementById("kSl").value) / 100}`;
    params += `&k_ma_filter=${document.getElementById("kMaFilter").checked}`;
    params += `&k_ma_period=${document.getElementById("kMaPeriod").value}`;
    params += `&k_volume_filter=${document.getElementById("kVolumeFilter").checked}`;
    params += `&k_volume_mult=${document.getElementById("kVolumeMult").value}`;
  } else if (strategy === "RSI_OVERSOLD_BOUNCE") {
    params += `&rsi_period=${document.getElementById("rsiPeriod").value}`;
    params += `&rsi_threshold=${document.getElementById("rsiThreshold").value}`;
    params += `&rsi_entry_mode=${document.getElementById("rsiEntryMode").value}`;
    params += `&rsi_use_tp=${document.getElementById("rsiUseTp").checked}`;
    params += `&rsi_tp=${parseFloat(document.getElementById("rsiTp").value) / 100}`;
    params += `&rsi_use_sl=${document.getElementById("rsiUseSl").checked}`;
    params += `&rsi_sl=${-parseFloat(document.getElementById("rsiSl").value) / 100}`;
    params += `&rsi_use_rsi_exit=${document.getElementById("rsiUseRsiExit").checked}`;
    params += `&rsi_exit=${document.getElementById("rsiExit").value}`;
    params += `&rsi_max_hold_bars=${document.getElementById("rsiMaxHoldBars").value}`;
    params += `&rsi_ma_filter=${document.getElementById("rsiMaFilter").checked}`;
    params += `&rsi_ma_period=${document.getElementById("rsiMaPeriod").value}`;
    params += `&rsi_volume_filter=${document.getElementById("rsiVolumeFilter").checked}`;
    params += `&rsi_volume_mult=${document.getElementById("rsiVolumeMult").value}`;
  } else if (strategy === "MA_GOLDEN_CROSS") {
    params += `&ma_fast=${document.getElementById("maFast").value}`;
    params += `&ma_slow=${document.getElementById("maSlow").value}`;
    params += `&ma_use_tp=${document.getElementById("maUseTp").checked}`;
    params += `&ma_tp=${parseFloat(document.getElementById("maTp").value) / 100}`;
    params += `&ma_use_sl=${document.getElementById("maUseSl").checked}`;
    params += `&ma_sl=${-parseFloat(document.getElementById("maSl").value) / 100}`;
    params += `&ma_use_ma_exit=${document.getElementById("mauseMAExit").checked}`;
    params += `&ma_volume_filter=${document.getElementById("maVolumeFilter").checked}`;
    params += `&ma_volume_mult=${document.getElementById("maVolumeMult").value}`;
    params += `&ma_max_hold_bars=${document.getElementById("maMaxHoldBars").value}`;
  } else if (strategy === "BOLLINGER_BOUNCE") {
    params += `&bb_period=${document.getElementById("bbPeriod").value}`;
    params += `&bb_std=${document.getElementById("bbStd").value}`;
    params += `&bb_use_tp=${document.getElementById("bbUseTp").checked}`;
    params += `&bb_tp=${parseFloat(document.getElementById("bbTp").value) / 100}`;
    params += `&bb_use_sl=${document.getElementById("bbUseSl").checked}`;
    params += `&bb_sl=${-parseFloat(document.getElementById("bbSl").value) / 100}`;
    params += `&bb_use_middle_exit=${document.getElementById("bbUseMiddleExit").checked}`;
    params += `&bb_volume_filter=${document.getElementById("bbVolumeFilter").checked}`;
    params += `&bb_volume_mult=${document.getElementById("bbVolumeMult").value}`;
    params += `&bb_max_hold_bars=${document.getElementById("bbMaxHoldBars").value}`;
  }

  const btn = document.getElementById("btRunBtn");
  btn.disabled = true;
  document.getElementById("btLoadingMsg").style.display = "block";
  document.getElementById("btLoadingText").textContent =
    `${STRATEGY_NAMES[strategy]} | ${INTERVAL_LABEL[interval]} ${count}개 캔들 수집 중...`;
  document.getElementById("btResult").style.display = "none";

  try {
    const res  = await fetch(`/api/backtesting?${params}`);
    const data = await res.json();
    if (data.error) { alert(data.error); return; }
    document.getElementById("btResult").style.display = "block";
    renderBacktest(data);
  } catch (e) {
    alert("백테스팅 오류: " + e.message);
  } finally {
    btn.disabled = false;
    document.getElementById("btLoadingMsg").style.display = "none";
  }
}

function renderCurrentSignal(sig, strategy, fmt) {
  const signalBox    = document.getElementById("signalBox");
  const signalBadge  = document.getElementById("signalBadge");
  const signalDetail = document.getElementById("signalDetail");

  if (!sig) {
    signalBox.className = "signal-box neutral";
    signalBadge.textContent = "신호 없음";
    signalDetail.innerHTML = "";
    return;
  }

  if (sig.triggered) {
    signalBox.className   = "signal-box triggered";
    signalBadge.className = "signal-badge triggered";
    signalBadge.textContent = "진입 신호 발생!";
  } else if (sig.in_trade) {
    signalBox.className   = "signal-box in-trade";
    signalBadge.className = "signal-badge in-trade";
    signalBadge.textContent = "포지션 보유 중";
  } else {
    signalBox.className   = "signal-box waiting";
    signalBadge.className = "signal-badge waiting";
    signalBadge.textContent = "대기 중";
  }

  let html = `<div class="signal-row"><span class="signal-label">날짜</span><span class="signal-value">${sig.date}</span></div>`;
  if (strategy === "K_VOLATILITY_BREAKOUT") {
    html += `
      <div class="signal-row"><span class="signal-label">시가</span><span class="signal-value">${fmt(sig.open)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">전일 범위</span><span class="signal-value">${fmt(sig.prev_range)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">목표가 (×K=${sig.k})</span><span class="signal-value">${fmt(sig.target_price)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">현재가</span><span class="signal-value">${fmt(sig.current_price)} ₩</span></div>`;
  } else if (strategy === "RSI_OVERSOLD_BOUNCE") {
    html += `
      <div class="signal-row"><span class="signal-label">RSI</span><span class="signal-value">${sig.rsi_value !== null ? sig.rsi_value : "-"}</span></div>
      <div class="signal-row"><span class="signal-label">진입 기준 (RSI &lt;)</span><span class="signal-value">${sig.threshold}</span></div>
      <div class="signal-row"><span class="signal-label">청산 기준 (RSI &ge;)</span><span class="signal-value">${sig.exit_threshold}</span></div>
      <div class="signal-row"><span class="signal-label">포지션</span><span class="signal-value">${sig.in_trade ? "보유 중" : "없음"}</span></div>`;
  } else if (strategy === "MA_GOLDEN_CROSS") {
    html += `
      <div class="signal-row"><span class="signal-label">단기 MA (${sig.fast_period})</span><span class="signal-value">${sig.ma_fast !== null ? fmt(sig.ma_fast) + " ₩" : "-"}</span></div>
      <div class="signal-row"><span class="signal-label">장기 MA (${sig.slow_period})</span><span class="signal-value">${sig.ma_slow !== null ? fmt(sig.ma_slow) + " ₩" : "-"}</span></div>
      <div class="signal-row"><span class="signal-label">포지션</span><span class="signal-value">${sig.in_trade ? "보유 중" : "없음"}</span></div>`;
  } else if (strategy === "BOLLINGER_BOUNCE") {
    html += `
      <div class="signal-row"><span class="signal-label">현재가</span><span class="signal-value">${fmt(sig.current_price)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">하단 밴드</span><span class="signal-value">${fmt(sig.lower_band)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">중간 밴드</span><span class="signal-value">${fmt(sig.middle_band)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">상단 밴드</span><span class="signal-value">${fmt(sig.upper_band)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">포지션</span><span class="signal-value">${sig.in_trade ? "보유 중" : "없음"}</span></div>`;
  }
  signalDetail.innerHTML = html;
}

function renderBtCandleChart() {
  const market   = document.getElementById("marketSelect").value;
  const interval = document.getElementById("intervalSelect").value;
  tvBtWidget = createTvWidget("btCandleChart", toTvSymbol(market), interval);
}

function renderBacktest(d) {
  const fmt = n => Number(n).toLocaleString("ko-KR");
  const pct = n => (n * 100).toFixed(2) + "%";

  renderBtCandleChart();
  renderCurrentSignal(d.current_signal, d.strategy, fmt);

  const setVal = (id, text, cls) => {
    const el = document.getElementById(id);
    el.textContent = text;
    el.className   = "s-value " + cls;
  };
  setVal("statTrades",      d.total_trades + "건",                                  "neutral");
  setVal("statWinRate",     pct(d.win_rate),                                        d.win_rate >= 0.5 ? "pos" : "neg");
  setVal("statAvgPnl",      (d.avg_pnl_per_trade >= 0 ? "+" : "") + pct(d.avg_pnl_per_trade), d.avg_pnl_per_trade >= 0 ? "pos" : "neg");
  setVal("statTotalReturn", (d.total_return >= 0 ? "+" : "") + pct(d.total_return), d.total_return >= 0 ? "pos" : "neg");
  setVal("statInitial",     fmt(d.initial_capital) + " ₩",                         "neutral money");
  setVal("statFinal",       fmt(d.final_value) + " ₩",                             (d.profit_loss >= 0 ? "pos" : "neg") + " money");
  setVal("statProfitLoss",  (d.profit_loss >= 0 ? "+" : "") + fmt(d.profit_loss) + " ₩", (d.profit_loss >= 0 ? "pos" : "neg") + " money");

  if (equityChart) { equityChart.destroy(); equityChart = null; }
  if (d.equity_curve && d.equity_curve.length > 0) {
    const ecLabels  = d.equity_curve.map(p => p.date);
    const ecValues  = d.equity_curve.map(p => p.value);
    const isProfit  = d.profit_loss >= 0;
    const lineColor = isProfit ? "#3fb950" : "#f85149";
    const ecCtx     = document.getElementById("equityChart").getContext("2d");
    equityChart = new Chart(ecCtx, {
      type: "line",
      data: {
        labels: ecLabels,
        datasets: [
          {
            label: "포트폴리오 가치",
            data: ecValues,
            borderColor: lineColor,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            fill: true,
            backgroundColor: isProfit ? "rgba(63,185,80,0.15)" : "rgba(248,81,73,0.15)",
            tension: 0.2,
          },
          {
            label: "원금",
            data: Array(ecValues.length).fill(d.initial_capital),
            borderColor: "#8b949e",
            borderWidth: 1,
            borderDash: [6, 4],
            pointRadius: 0,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { color: "#8b949e", font: { size: 12 } } },
          tooltip: {
            backgroundColor: "#161b22",
            borderColor: "#30363d",
            borderWidth: 1,
            titleColor: "#8b949e",
            bodyColor: "#e6edf3",
            callbacks: {
              label: ctx => {
                const val = ctx.parsed.y;
                if (ctx.datasetIndex === 0) {
                  const chg  = (val - d.initial_capital) / d.initial_capital * 100;
                  const sign = chg >= 0 ? "+" : "";
                  return ` ${Number(val).toLocaleString("ko-KR")} ₩  (원금대비 ${sign}${chg.toFixed(2)}%)`;
                }
                return ` ${Number(val).toLocaleString("ko-KR")} ₩`;
              },
            },
          },
        },
        scales: {
          x: { ticks: { color: "#8b949e", maxTicksLimit: 10 }, grid: { color: "#21262d" } },
          y: { ticks: { color: "#8b949e", callback: v => Number(v).toLocaleString("ko-KR") }, grid: { color: "#21262d" } },
        },
      },
    });
  }

  const tbody  = document.getElementById("tradesBody");
  const trades = [...d.trades].reverse().slice(0, 50);
  document.getElementById("tradesTitle").textContent = `최근 거래 내역 (${trades.length}건)`;
  tbody.innerHTML = trades.map((t, idx) => {
    const isOpen    = !!t.open;
    const pnlColor  = isOpen ? "#8b949e" : (t.pnl >= 0 ? "#3fb950" : "#f85149");
    const pnlText   = (t.pnl >= 0 ? "+" : "") + pct(t.pnl) + (isOpen ? " *" : "");
    const krwText   = isOpen ? "-" : `<span style="color:${t.krw_pnl >= 0 ? "#3fb950" : "#f85149"}">${(t.krw_pnl >= 0 ? "+" : "") + fmt(t.krw_pnl)} ₩</span>`;
    const statusText = isOpen ? `<span style="color:#e3b341">보유중</span>` : `<span style="color:${t.win ? "#3fb950" : "#f85149"}">${t.win ? "✓ 수익" : "✗ 손실"}</span>`;
    return `<tr${isOpen ? ' style="background:rgba(227,179,65,0.06)"' : ''}>
      <td style="text-align:center;color:#8b949e">${trades.length - idx}</td>
      <td style="text-align:left;color:#8b949e">${(t.buy_datetime  || "").slice(0,16).replace("T"," ")}</td>
      <td style="text-align:left;color:#8b949e">${(t.sell_datetime || "").slice(0,16).replace("T"," ")}</td>
      <td>${fmt(t.buy_price)} ₩</td>
      <td>${fmt(t.sell_price)} ₩</td>
      <td style="color:${pnlColor}">${pnlText}</td>
      <td>${krwText}</td>
      <td>${statusText}</td>
    </tr>`;
  }).join("");
}

// ── 초기 로드 ────────────────────────────────────────────
loadMarkets();
updateStrategyDesc();
refreshKeyStatus();

setInterval(() => {
  const market = document.getElementById("marketSelect").value;
  if (market) loadTicker(market);
}, 30000);

// ── 실시간 매매 ──────────────────────────────────────────
let ltActive = false;
let ltStatusTimer = null;

function syncLtMarkets() {
  const src = document.getElementById("marketSelect");
  const dst = document.getElementById("ltMarket");
  dst.innerHTML = src.innerHTML;
  dst.value     = src.value;
}

document.getElementById("marketSelect").addEventListener("change", syncLtMarkets);

// 탭 진입 시 키 파일 경로 및 섹션별 설정 상태 표시, 실시간 매매 탭 버튼 활성/비활성 제어
async function refreshKeyStatus() {
  try {
    const res = await fetch("/api/trading/keys");
    const d   = await res.json();
    const pathEl = document.getElementById("ltKeyFilePath");
    if (pathEl) {
      const raw = d.key_file || "-";
      const fileName = raw === "-" ? raw : raw.replace(/^.*[/\\]/, "");
      pathEl.textContent = fileName;
    }
    [
      { id: "ltKeyStatusBalance",    has: d.has_balance },
      { id: "ltKeyStatusOrderQuery", has: d.has_order_query },
      { id: "ltKeyStatusOrder",      has: d.has_order },
    ].forEach(({ id, has }) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = has ? "✓" : "미설정";
      el.style.color = has ? "#3fb950" : "#f85149";
    });

    _keysAllSet = !!d.has_all;
    const liveTradingBtn = document.querySelector('.tab-btn[data-tab="live-trading"]');
    if (liveTradingBtn) {
      if (_keysAllSet) {
        liveTradingBtn.classList.remove("disabled-clickable");
        liveTradingBtn.title = "";
      } else {
        liveTradingBtn.classList.add("disabled-clickable");
        liveTradingBtn.title = "upbit_keys 파일에 API 키를 등록해주세요";
      }
    }
  } catch (e) {}
}

async function testConnection() {
  const statusEl = document.getElementById("ltConnStatus");
  statusEl.textContent = "연결 중..."; statusEl.style.color = "#8b949e";
  try {
    const res = await fetch("/api/trading/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        market:            document.getElementById("ltMarket").value,
        strategy:          document.getElementById("ltStrategy").value,
        timeframe:         document.getElementById("ltTimeframe").value,
        position_size_pct: parseFloat(document.getElementById("ltPositionPct").value) / 100,
      }),
    });
    const d = await res.json();
    if (res.ok) {
      statusEl.textContent = d.message; statusEl.style.color = "#3fb950";
      refreshBalance();
    } else {
      statusEl.textContent = d.error; statusEl.style.color = "#f85149";
    }
  } catch (e) {
    statusEl.textContent = "요청 실패"; statusEl.style.color = "#f85149";
  }
}

async function startTrading() {
  const market = document.getElementById("ltMarket").value;
  if (!market) { alert("마켓을 선택해주세요"); return; }

  const strategy  = document.getElementById("ltStrategy").options[document.getElementById("ltStrategy").selectedIndex].text;
  const timeframe = document.getElementById("ltTimeframe").options[document.getElementById("ltTimeframe").selectedIndex].text;
  const pct       = document.getElementById("ltPositionPct").value;
  if (!confirm(`자동매매를 시작하시겠습니까?\n\n마켓: ${market}\n전략: ${strategy}\n타임프레임: ${timeframe}\n포지션 크기: ${pct}%\n\n실제 자금으로 거래됩니다.`)) return;

  try {
    const res = await fetch("/api/trading/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        market,
        strategy:          document.getElementById("ltStrategy").value,
        timeframe:         document.getElementById("ltTimeframe").value,
        position_size_pct: parseFloat(document.getElementById("ltPositionPct").value) / 100,
      }),
    });
    const d = await res.json();
    if (res.ok) {
      ltActive = true;
      document.getElementById("ltStartBtn").disabled = true;
      document.getElementById("ltStopBtn").disabled  = false;
      document.getElementById("ltDot").className = "lt-status-dot on";
      document.getElementById("ltRunStatus").innerHTML = '<span class="lt-status-dot on" id="ltDot"></span>자동매매 실행 중';
      refreshStatus();
      ltStatusTimer = setInterval(refreshStatus, 10000);
    } else {
      alert("시작 실패: " + d.error);
    }
  } catch (e) {
    alert("요청 실패");
  }
}

async function stopTrading() {
  const market = document.getElementById("ltMarket").value;
  try {
    const res = await fetch("/api/trading/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ market }),
    });
    if (res.ok) {
      ltActive = false;
      document.getElementById("ltStartBtn").disabled = false;
      document.getElementById("ltStopBtn").disabled  = true;
      document.getElementById("ltRunStatus").innerHTML = '<span class="lt-status-dot off" id="ltDot"></span>대기 중';
      if (ltStatusTimer) { clearInterval(ltStatusTimer); ltStatusTimer = null; }
      refreshStatus();
    }
  } catch (e) { alert("요청 실패"); }
}

function renderPositionCard(card, body, position, pnl, isManual) {
  if (position) {
    const p          = pnl || {};
    const pnlPct     = p.unrealized_pnl_pct !== undefined ? p.unrealized_pnl_pct : 0;
    const pnlKrw     = p.unrealized_pnl_krw !== undefined ? p.unrealized_pnl_krw : 0;
    const color       = pnlPct >= 0 ? "#3fb950" : "#f85149";
    card.style.borderColor = isManual ? "#238636" : "#1c6ef3";
    card.className    = "lt-position-card";
    const closeBtn    = isManual
      ? `<button class="lt-btn lt-btn-stop" style="padding:3px 10px;font-size:0.75rem;margin-top:10px;" onclick="closeManualPosition()">포지션 청산</button>`
      : "";
    body.innerHTML = `<div class="lt-pos-grid">
      <div class="lt-pos-item"><div class="lt-pos-label">마켓</div><div class="lt-pos-value">${position.market}</div></div>
      <div class="lt-pos-item"><div class="lt-pos-label">전략</div><div class="lt-pos-value" style="font-size:0.82rem">${position.strategy}</div></div>
      <div class="lt-pos-item"><div class="lt-pos-label">진입가</div><div class="lt-pos-value">${Number(position.entry_price).toLocaleString("ko-KR")} ₩</div></div>
      <div class="lt-pos-item"><div class="lt-pos-label">현재가</div><div class="lt-pos-value">${p.current_price ? Number(p.current_price).toLocaleString("ko-KR")+"₩" : "-"}</div></div>
      <div class="lt-pos-item"><div class="lt-pos-label">수량</div><div class="lt-pos-value">${Number(position.quantity).toFixed(8)}</div></div>
      <div class="lt-pos-item"><div class="lt-pos-label">미실현 손익</div><div class="lt-pos-value" style="color:${color}">${(pnlPct*100).toFixed(2)}% (${pnlKrw>=0?"+":""}${Math.round(pnlKrw).toLocaleString("ko-KR")}₩)</div></div>
      <div class="lt-pos-item"><div class="lt-pos-label">진입일시</div><div class="lt-pos-value" style="font-size:0.78rem;font-weight:400">${(position.entry_datetime||"").slice(0,16).replace("T"," ")}</div></div>
    </div>${closeBtn}`;
  } else {
    card.className = "lt-position-card empty";
    card.style.borderColor = "";
    body.innerHTML = '<span style="color:#8b949e;font-size:0.88rem;">포지션 없음</span>';
  }
}

function toggleManualPositionForm() {
  const form    = document.getElementById("ltManualPositionForm");
  const visible = form.style.display !== "none";
  form.style.display = visible ? "none" : "block";
  if (!visible) {
    const market = document.getElementById("ltMarket").value || document.getElementById("marketSelect").value;
    if (market) document.getElementById("mpMarket").value = market;
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById("mpEntryDatetime").value = now.toISOString().slice(0,16);
  }
}

async function registerManualPosition() {
  const market        = document.getElementById("mpMarket").value.trim().toUpperCase();
  const entryPrice    = parseFloat(document.getElementById("mpEntryPrice").value);
  const quantity      = parseFloat(document.getElementById("mpQuantity").value);
  const entryDatetime = document.getElementById("mpEntryDatetime").value;
  if (!market || !entryPrice || !quantity || !entryDatetime) {
    alert("모든 필드를 입력해주세요."); return;
  }
  const res = await fetch("/api/trading/position/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ market, entry_price: entryPrice, quantity, entry_datetime: new Date(entryDatetime).toISOString() }),
  });
  const d = await res.json();
  if (res.ok) { toggleManualPositionForm(); refreshStatus(); }
  else alert("등록 실패: " + d.error);
}

async function closeManualPosition() {
  if (!confirm("수동 포지션을 청산하시겠습니까?\n현재가로 청산 기록됩니다.")) return;
  const res = await fetch("/api/trading/position/manual", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ exit_reason: "manual_close" }),
  });
  const d = await res.json();
  if (res.ok) refreshStatus();
  else alert("청산 실패: " + d.error);
}

async function refreshStatus() {
  try {
    const res = await fetch("/api/trading/status");
    const d   = await res.json();

    const running = d.scheduler && d.scheduler.running && d.scheduler.active_markets && d.scheduler.active_markets.length > 0;
    if (running !== ltActive) {
      ltActive = running;
      document.getElementById("ltStartBtn").disabled = running;
      document.getElementById("ltStopBtn").disabled  = !running;
      document.getElementById("ltRunStatus").innerHTML = running
        ? '<span class="lt-status-dot on" id="ltDot"></span>자동매매 실행 중'
        : '<span class="lt-status-dot off" id="ltDot"></span>대기 중';
      if (running  && !ltStatusTimer) ltStatusTimer = setInterval(refreshStatus, 10000);
      if (!running && ltStatusTimer)  { clearInterval(ltStatusTimer); ltStatusTimer = null; }
    }

    renderPositionCard(
      document.getElementById("ltAutoPositionCard"),
      document.getElementById("ltAutoPositionBody"),
      d.auto_position || d.position, d.pnl, false
    );
    renderPositionCard(
      document.getElementById("ltManualPositionCard"),
      document.getElementById("ltManualPositionBody"),
      d.manual_position, d.manual_pnl, true
    );

    if (d.balance) {
      document.getElementById("ltBalanceBody").innerHTML =
        `KRW 가용: <strong style="color:#e6edf3">${Math.floor(d.balance.krw_balance).toLocaleString("ko-KR")} ₩</strong>
        &nbsp; 대기주문: <strong style="color:#8b949e">${Math.floor(d.balance.krw_locked).toLocaleString("ko-KR")} ₩</strong>
        ${d.balance.coin_balance > 0 ? ` &nbsp; 코인: <strong style="color:#e6edf3">${d.balance.coin_balance}</strong>` : ""}`;
    }
  } catch (e) {}

  refreshOrders();
}

async function refreshBalance() {
  try {
    const res = await fetch("/api/trading/balance");
    if (!res.ok) return;
    const d = await res.json();
    document.getElementById("ltBalanceBody").innerHTML =
      `KRW 가용: <strong style="color:#e6edf3">${Math.floor(d.krw_balance).toLocaleString("ko-KR")} ₩</strong>
      &nbsp; 대기주문: <strong style="color:#8b949e">${Math.floor(d.krw_locked).toLocaleString("ko-KR")} ₩</strong>
      ${d.coin_balance > 0 ? ` &nbsp; 코인: <strong style="color:#e6edf3">${d.coin_balance}</strong>` : ""}`;
  } catch (e) {}
}

async function refreshOrders() {
  try {
    const [ordRes, tradeRes] = await Promise.all([
      fetch("/api/trading/orders"),
      fetch("/api/trading/trades"),
    ]);
    const { orders } = await ordRes.json();
    const { trades } = await tradeRes.json();
    const fmt = n => Number(n).toLocaleString("ko-KR");

    const ordBody = document.getElementById("ltOrdersBody");
    if (orders && orders.length > 0) {
      ordBody.innerHTML = orders.map((o, i) => {
        const side = o.side === "bid"
          ? '<span style="color:#3fb950">매수</span>'
          : '<span style="color:#f85149">매도</span>';
        return `<tr>
          <td>${orders.length - i}</td>
          <td style="text-align:left">${side}</td>
          <td style="text-align:left">${o.market}</td>
          <td>${o.price > 0 ? fmt(o.price)+" ₩" : "-"}</td>
          <td>${o.volume}</td>
          <td>${o.executed_funds > 0 ? fmt(Math.round(o.executed_funds))+" ₩" : "-"}</td>
          <td style="text-align:left;font-size:0.78rem;color:#8b949e">${(o.created_at||"").slice(0,16).replace("T"," ")}</td>
          <td><span style="color:${o.status==="done"?"#3fb950":"#8b949e"}">${o.status}</span></td>
        </tr>`;
      }).join("");
    } else {
      ordBody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#8b949e;padding:20px;">주문 없음</td></tr>';
    }

    const exitLabels = { take_profit: "익절", stop_loss: "손절", strategy_signal: "전략신호" };
    const tradeBody  = document.getElementById("ltTradesBody");
    if (trades && trades.length > 0) {
      tradeBody.innerHTML = trades.map((t, i) => {
        const pnl   = t.pnl_pct || 0;
        const color = pnl >= 0 ? "#3fb950" : "#f85149";
        return `<tr>
          <td>${trades.length - i}</td>
          <td style="text-align:left;color:#8b949e;font-size:0.78rem">${(t.buy_datetime  ||"").slice(0,16).replace("T"," ")}</td>
          <td style="text-align:left;color:#8b949e;font-size:0.78rem">${(t.sell_datetime ||"").slice(0,16).replace("T"," ")}</td>
          <td>${fmt(Math.round(t.buy_price))} ₩</td>
          <td>${fmt(Math.round(t.sell_price))} ₩</td>
          <td style="color:${color}">${(pnl*100).toFixed(2)}%</td>
          <td style="color:${color}">${(t.pnl_krw>=0?"+":"")+fmt(t.pnl_krw)} ₩</td>
          <td style="text-align:left">${exitLabels[t.exit_reason]||t.exit_reason}</td>
        </tr>`;
      }).join("");
    } else {
      tradeBody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#8b949e;padding:20px;">거래 없음</td></tr>';
    }
  } catch (e) {}
}

// 실시간 매매 탭 클릭 시 상태 및 마켓 동기화
document.querySelector(".tabs").addEventListener("click", e => {
  if (e.target.dataset && e.target.dataset.tab === "live-trading" && _keysAllSet) {
    syncLtMarkets();
    refreshStatus();
    refreshKeyStatus();
  }
});
