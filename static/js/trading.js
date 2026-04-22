let ltActive = false;
let ltStatusTimer = null;

function syncLtMarkets() {
  const src = document.getElementById("marketSelect");
  const dst = document.getElementById("ltMarket");
  dst.innerHTML = src.innerHTML;
  dst.value     = src.value;
}

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
