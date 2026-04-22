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
