// 백테스팅 결과 렌더링 진입점
// 차트 렌더링: backtesting_charts.js

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

  let html = `<div class="signal-row"><span class="signal-label">날짜</span><span class="signal-value">${sig.date.replace("T", " ")}</span></div>`;
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
  } else if (strategy === "TRAILING_BREAKOUT") {
    html += `
      <div class="signal-row"><span class="signal-label">시가</span><span class="signal-value">${fmt(sig.open)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">전일 범위</span><span class="signal-value">${fmt(sig.prev_range)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">목표가 (×K=${sig.k})</span><span class="signal-value">${fmt(sig.target_price)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">손절가 (SL)</span><span class="signal-value">${fmt(sig.sl_price)} ₩</span></div>
      <div class="signal-row"><span class="signal-label">트레일링 갭</span><span class="signal-value">${sig.trail_pct}%</span></div>
      <div class="signal-row"><span class="signal-label">현재가</span><span class="signal-value">${fmt(sig.current_price)} ₩</span></div>`;
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

function renderBacktest(d) {
  // 정수면 쉼표 구분, 소수점 있으면 최대 8자리까지 표시 (불필요한 trailing zero 제거)
  const fmt = n => {
    const num = Number(n);
    if (!isFinite(num)) return "-";
    if (Number.isInteger(num)) return num.toLocaleString("ko-KR");
    const [int, dec] = num.toFixed(8).split(".");
    const trimmed = dec.replace(/0+$/, "");
    return Number(int).toLocaleString("ko-KR") + (trimmed ? "." + trimmed : "");
  };
  const pct = n => (n * 100).toFixed(2) + "%";

  renderBtCandleChart(d);
  renderBtRsiChart(d);
  renderEquityChart(d);
  renderCurrentSignal(d.current_signal, d.strategy, fmt);

  const setVal = (id, text, cls) => {
    const el = document.getElementById(id);
    el.textContent = text;
    el.className   = "s-value " + cls;
  };
  setVal("statTrades",      d.total_trades + "건",                                  "neutral");
  setVal("statWinRate",     pct(d.win_rate),                                        d.win_rate >= 0.5 ? "pos" : "neg");
  setVal("statTotalReturn", (d.total_return >= 0 ? "+" : "") + pct(d.total_return), d.total_return >= 0 ? "pos" : "neg");
  setVal("statInitial",     fmt(d.initial_capital) + " ₩",                         "neutral money");
  setVal("statFinal",       fmt(d.final_value) + " ₩",                             (d.profit_loss >= 0 ? "pos" : "neg") + " money");
  setVal("statProfitLoss",  (d.profit_loss >= 0 ? "+" : "") + fmt(d.profit_loss) + " ₩", (d.profit_loss >= 0 ? "pos" : "neg") + " money");

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
      <td style="color:#8b949e">${t.entry_amount != null ? fmt(t.entry_amount) + " ₩" : "-"}</td>
      <td style="color:#8b949e">${t.fee != null ? fmt(t.fee) + " ₩" : "-"}</td>
      <td style="color:${pnlColor}">${pnlText}</td>
      <td>${krwText}</td>
      <td style="color:#8b949e">${(() => {
        if (t.entry_amount == null) return "-";
        // 보유중(청산 미완료): 진입 시드에서 수수료만 차감
        // 청산 완료: 진입 시드에서 손익과 수수료를 반영
        const seed = isOpen
          ? t.entry_amount - (t.fee || 0)
          : t.entry_amount + (t.krw_pnl || 0) - (t.fee || 0);
        return fmt(seed) + " ₩";
      })()}</td>
      <td>${statusText}</td>
    </tr>`;
  }).join("");
}
