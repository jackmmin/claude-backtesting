// 실시간 매매 API 호출 모음

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
    // 키 파일 설정 여부와 무관하게 연결테스트 전에는 항상 ✗ 표시
    ["ltKeyStatusBalance", "ltKeyStatusOrderQuery", "ltKeyStatusOrder"].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = "✗";
      el.style.color  = "#f85149";
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
  } catch (e) {
    showToast("키 상태 확인 실패: " + e.message);
  }
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
    _applyKeyStatus(d.key_status);
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
  if (!market) { showToast("마켓을 선택해주세요"); return; }

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
      showToast("시작 실패: " + (d.error || "알 수 없는 오류"));
    }
  } catch (e) {
    showToast("자동매매 시작 요청 실패: " + e.message);
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
    } else {
      const d = await res.json().catch(() => ({}));
      showToast("중지 실패: " + (d.error || "알 수 없는 오류"));
    }
  } catch (e) {
    showToast("자동매매 중지 요청 실패: " + e.message);
  }
}

async function registerManualPosition() {
  const market        = document.getElementById("mpMarket").value.trim().toUpperCase();
  const entryPrice    = parseFloat(document.getElementById("mpEntryPrice").value);
  const quantity      = parseFloat(document.getElementById("mpQuantity").value);
  const entryDatetime = document.getElementById("mpEntryDatetime").value;
  if (!market || !entryPrice || !quantity || !entryDatetime) {
    showToast("모든 필드를 입력해주세요."); return;
  }
  try {
    const res = await fetch("/api/trading/position/manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ market, entry_price: entryPrice, quantity, entry_datetime: new Date(entryDatetime).toISOString() }),
    });
    const d = await res.json();
    if (res.ok) { toggleManualPositionForm(); refreshStatus(); }
    else showToast("등록 실패: " + (d.error || "알 수 없는 오류"));
  } catch (e) {
    showToast("포지션 등록 요청 실패: " + e.message);
  }
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

async function refreshBalance() {
  try {
    const res = await fetch("/api/trading/balance");
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      showToast("잔액 조회 실패: " + (d.error || `서버 오류 (${res.status})`));
      return;
    }
    const d = await res.json();
    document.getElementById("ltBalanceBody").innerHTML =
      `KRW 가용: <strong style="color:#e6edf3">${Math.floor(d.krw_balance).toLocaleString("ko-KR")} ₩</strong>
      &nbsp; 대기주문: <strong style="color:#8b949e">${Math.floor(d.krw_locked).toLocaleString("ko-KR")} ₩</strong>
      ${d.coin_balance > 0 ? ` &nbsp; 코인: <strong style="color:#e6edf3">${d.coin_balance}</strong>` : ""}`;
  } catch (e) {
    showToast("잔액 조회 요청 실패: " + e.message);
  }
}

async function refreshOrders() {
  try {
    const [ordRes, tradeRes] = await Promise.all([
      fetch("/api/trading/orders"),
      fetch("/api/trading/trades"),
    ]);
    if (!ordRes.ok || !tradeRes.ok) {
      console.warn("주문/거래 내역 조회 실패");
      return;
    }
    const { orders } = await ordRes.json();
    const { trades } = await tradeRes.json();
    renderOrders(orders);
    renderTrades(trades);
  } catch (e) {
    console.warn("주문/거래 내역 로드 실패:", e.message);
  }
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

    // 새 스케줄러 이벤트 발생 시 토스트 표시
    if (d.last_event && d.last_event.timestamp !== _lastEventTs) {
      _lastEventTs = d.last_event.timestamp;
      if (d.last_event.type === "position_exists") {
        showToast("⚠ " + d.last_event.message);
      }
    }
  } catch (e) {
    console.warn("상태 조회 실패:", e.message);
  }

  refreshOrders();
}
