// 실시간 매매 UI 렌더링 모음

// STRATEGY_OVERVIEW는 backtesting_ui.js에 정의된 공통 객체를 참조
function updateLtStrategyDesc() {
  const strategy = document.getElementById("ltStrategy").value;
  const el = document.getElementById("ltStrategyDesc");
  if (!el) return;
  el.textContent = (typeof STRATEGY_OVERVIEW !== "undefined" && STRATEGY_OVERVIEW[strategy]) || "";
}

function syncLtMarkets() {
  const src = document.getElementById("marketSelect");
  const dst = document.getElementById("ltMarket");
  dst.innerHTML = src.innerHTML;
  dst.value     = src.value;
}

function _applyKeyStatus(key_status) {
  if (!key_status) return;
  const map = [
    { id: "ltKeyStatusBalance",    ok: key_status.balance },
    { id: "ltKeyStatusOrderQuery", ok: key_status.order_query },
    { id: "ltKeyStatusOrder",      ok: key_status.order },
  ];
  map.forEach(({ id, ok }) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = ok ? "✓" : "✗";
    el.style.color  = ok ? "#3fb950" : "#f85149";
  });
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

function renderOrders(orders) {
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
}

function renderTrades(trades) {
  const fmt = n => Number(n).toLocaleString("ko-KR");
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
}
