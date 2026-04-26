// 백테스팅 차트 렌더링 (캔들, RSI, 에쿼티)

let equityChart = null;
let btRsiLwChart = null;

function renderBtCandleChart(d) {
  const container = document.getElementById("btCandleChart");
  container.innerHTML = "";
  if (btLwChart) { btLwChart.remove(); btLwChart = null; }
  if (!d || !d.candles || d.candles.length === 0) return;

  btLwChart = LightweightCharts.createChart(container, {
    layout: { background: { color: "#0d1117" }, textColor: "#8b949e" },
    grid: { vertLines: { color: "#21262d" }, horzLines: { color: "#21262d" } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: "#30363d" },
    timeScale: { borderColor: "#30363d", timeVisible: true, secondsVisible: false },
    width: container.clientWidth,
    height: container.clientHeight || 400,
  });

  const candleSeries = btLwChart.addCandlestickSeries({
    upColor: "#3fb950", downColor: "#f85149",
    borderUpColor: "#3fb950", borderDownColor: "#f85149",
    wickUpColor: "#3fb950", wickDownColor: "#f85149",
  });

  // KST 시간을 UTC 기준 Unix 초로 변환 (timezone offset 제거)
  const toChartTime = t => {
    const clean = t.replace(/\+09:00$/, "").replace(" ", "T");
    return Math.floor(new Date(clean + "Z").getTime() / 1000);
  };

  candleSeries.setData(d.candles.map(c => ({
    time: toChartTime(c.t), open: c.o, high: c.h, low: c.l, close: c.c,
  })));

  // 매수/매도 마커
  if (d.trade_markers && d.trade_markers.length > 0) {
    const markers = [];
    for (const m of d.trade_markers) {
      if (m.buy_datetime)  markers.push({ time: toChartTime(m.buy_datetime),  position: "belowBar", color: "#3fb950", shape: "arrowUp",   text: "B" });
      if (m.sell_datetime) markers.push({ time: toChartTime(m.sell_datetime), position: "aboveBar", color: m.win ? "#3fb950" : "#f85149", shape: "arrowDown", text: "S" });
    }
    markers.sort((a, b) => a.time - b.time);
    candleSeries.setMarkers(markers);
  }

  // 볼륨 히스토그램 (차트 하단 20% 영역에 오버레이)
  const volumeSeries = btLwChart.addHistogramSeries({
    priceFormat: { type: "volume" },
    priceScaleId: "volume",
  });
  btLwChart.priceScale("volume").applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 },
    visible: false,
  });
  volumeSeries.setData(d.candles.map(c => ({
    time: toChartTime(c.t),
    value: c.v || 0,
    color: c.c >= c.o ? "rgba(63,185,80,0.4)" : "rgba(248,81,73,0.4)",
  })));

  // 활성화된 MA 필터 라인 오버레이 (단기=파랑, 중기=주황, 장기=보라)
  const MA_COLORS = ["#58a6ff", "#f0883e", "#bc8cff"];
  (d.ma_lines || []).forEach((ml, idx) => {
    if (!ml || !ml.data) return;
    const maSeries = btLwChart.addLineSeries({
      color: MA_COLORS[idx % MA_COLORS.length],
      lineWidth: 1.5,
      title: `MA${ml.period}`,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    maSeries.setData(
      d.candles
        .map((c, i) => ml.data[i] != null ? { time: toChartTime(c.t), value: ml.data[i] } : null)
        .filter(v => v !== null)
    );
  });

  btLwChart.timeScale().fitContent();

  new ResizeObserver(() => {
    if (btLwChart) btLwChart.applyOptions({ width: container.clientWidth, height: container.clientHeight || 400 });
  }).observe(container);
}

function renderBtRsiChart(d) {
  const wrap      = document.getElementById("btRsiChartWrap");
  const container = document.getElementById("btRsiChart");
  if (btRsiLwChart) { btRsiLwChart.remove(); btRsiLwChart = null; }

  // RSI 데이터가 없거나 전략이 RSI 무관이면 숨김
  if (!d.rsi_line || d.rsi_line.length === 0) {
    wrap.style.display = "none";
    return;
  }
  wrap.style.display = "block";
  container.innerHTML = "";

  const toChartTime = t => {
    const clean = t.replace(/\+09:00$/, "").replace(" ", "T");
    return Math.floor(new Date(clean + "Z").getTime() / 1000);
  };

  btRsiLwChart = LightweightCharts.createChart(container, {
    layout: { background: { color: "#0d1117" }, textColor: "#8b949e" },
    grid: { vertLines: { color: "#21262d" }, horzLines: { color: "#21262d" } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: "#30363d", scaleMargins: { top: 0.1, bottom: 0.1 } },
    timeScale: { borderColor: "#30363d", timeVisible: true, secondsVisible: false },
    width: container.clientWidth,
    height: container.clientHeight || 160,
  });

  // RSI 라인
  const rsiSeries = btRsiLwChart.addLineSeries({
    color: "#c084fc",
    lineWidth: 1.5,
    title: `RSI(${d.rsi_period || 14})`,
    priceLineVisible: false,
    lastValueVisible: true,
  });
  const rsiData = d.candles
    .map((c, i) => d.rsi_line[i] != null ? { time: toChartTime(c.t), value: d.rsi_line[i] } : null)
    .filter(v => v !== null);
  rsiSeries.setData(rsiData);

  // 과매도(30) / 과매수(70) 기준선
  const makeBaseline = (val, color) => {
    const s = btRsiLwChart.addLineSeries({
      color, lineWidth: 2, lineStyle: 0,
      priceLineVisible: false, lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
    s.setData(rsiData.map(p => ({ time: p.time, value: val })));
  };
  makeBaseline(70, "rgba(63,185,80,0.5)");
  makeBaseline(30, "rgba(248,81,73,0.5)");
  makeBaseline(50, "rgba(139,148,158,0.3)");

  // RSI_DIVERGENCE_TRAIL: 다이버전스 저점 마커 표시
  if (d.strategy === "RSI_DIVERGENCE_TRAIL" && d.divergence_points && d.divergence_points.length > 0) {
    const divMarkers = [];
    for (const idx of d.divergence_points) {
      if (!d.candles[idx] || d.rsi_line[idx] == null) continue;
      divMarkers.push({
        time: toChartTime(d.candles[idx].t),
        position: "belowBar",
        color: "#f0883e",
        shape: "circle",
        text: "D",
        size: 1,
      });
    }
    divMarkers.sort((a, b) => a.time - b.time);
    rsiSeries.setMarkers(divMarkers);
  }

  btRsiLwChart.timeScale().fitContent();

  // 캔들 차트와 시간축 동기화
  if (btLwChart) {
    btLwChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (range && btRsiLwChart) btRsiLwChart.timeScale().setVisibleLogicalRange(range);
    });
    btRsiLwChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (range && btLwChart) btLwChart.timeScale().setVisibleLogicalRange(range);
    });
  }

  new ResizeObserver(() => {
    if (btRsiLwChart) btRsiLwChart.applyOptions({ width: container.clientWidth, height: container.clientHeight || 160 });
  }).observe(container);
}

function renderEquityChart(d) {
  if (equityChart) { equityChart.destroy(); equityChart = null; }
  if (!d.equity_curve || d.equity_curve.length === 0) return;

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
