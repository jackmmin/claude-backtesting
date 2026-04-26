let _toastTimer = null;
let _keysAllSet = false;

// ── 토스트 알림 ─────────────────────────────────────────
function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  if (_toastTimer) clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}

// ── 탭 전환 ────────────────────────────────────────────
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

// ── 이벤트 바인딩 ───────────────────────────────────────
document.getElementById("marketSelect").addEventListener("change", () => {
  const activeTab = document.querySelector(".tab-pane.active").id;
  if (activeTab === "tab-chart") loadTvChart();
});

document.getElementById("chartIntervalSelect").addEventListener("change", loadTvChart);
document.getElementById("marketSelect").addEventListener("change", syncLtMarkets);
document.getElementById("btRunBtn").addEventListener("click", runBacktest);
document.getElementById("ltStrategy").addEventListener("change", updateLtStrategyDesc);

// 실시간 매매 탭 클릭 시 상태 및 마켓 동기화
document.querySelector(".tabs").addEventListener("click", e => {
  if (e.target.dataset && e.target.dataset.tab === "live-trading" && _keysAllSet) {
    syncLtMarkets();
    refreshStatus();
    refreshKeyStatus();
  }
});

// ── 초기 로드 ────────────────────────────────────────────
loadMarkets();
updateStrategyDesc();
updateLtStrategyDesc();
refreshKeyStatus();

// 탭이 숨겨져 있으면 폴링 건너뜀 (불필요한 서버 요청 방지)
let _tickerTimer = setInterval(() => {
  if (document.hidden) return;
  const market = document.getElementById("marketSelect").value;
  if (market) loadTicker(market);
}, 30000);

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) {
    // 탭 복귀 시 즉시 갱신
    const market = document.getElementById("marketSelect").value;
    if (market) loadTicker(market);
  }
});
