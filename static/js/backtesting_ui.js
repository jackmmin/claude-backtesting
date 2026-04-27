const STRATEGY_NAMES = {
  K_VOLATILITY_BREAKOUT: "K변동성 돌파",
  TRAILING_BREAKOUT:     "트레일링 스탑 돌파",
  RSI_OVERSOLD_BOUNCE:   "RSI 과매도 반등",
  RSI_DIVERGENCE_TRAIL:  "RSI 다이버전스 + 트레일링",
  MA_GOLDEN_CROSS:       "MA 골든크로스",
  BOLLINGER_BOUNCE:      "볼린저밴드 반등",
};

const STRATEGY_OVERVIEW = {
  K_VOLATILITY_BREAKOUT: "전일 변동폭의 K배를 시가에 더한 가격을 돌파하면 매수. 추세 추종형으로 변동성이 클수록 유리하며, TP/SL로 수익과 손실을 제한합니다.",
  RSI_OVERSOLD_BOUNCE:   "RSI가 과매도 구간에 진입할 때 반등을 노리는 평균 회귀 전략. 횡보장에서 유효하며 추세장에서는 손실이 커질 수 있습니다.",
  RSI_DIVERGENCE_TRAIL:  "가격은 신저점인데 RSI는 오히려 올라오는 상승 다이버전스 + 거래량 급증 시 진입. 추세 전환 초입을 포착하며 트레일링 스탑으로 수익을 극대화합니다.",
  MA_GOLDEN_CROSS:       "단기 이동평균이 장기 이동평균을 상향 돌파(골든크로스)할 때 매수. 중·장기 추세 추종 전략으로 추세가 뚜렷한 시장에서 강합니다.",
  BOLLINGER_BOUNCE:      "볼린저밴드 하단을 이탈한 가격이 밴드 안으로 복귀할 때 매수. 과매도 반등을 노리는 평균 회귀 전략입니다.",
  TRAILING_BREAKOUT:     "변동성 돌파로 진입 후 즉시 타이트한 손절로 손실을 제한하고, 고점 대비 일정 % 하락 시 청산(트레일링)으로 수익을 극대화. 손익비 중심 단기 전략.",
};

const INTERVAL_LABEL = {
  minutes15: "15분봉", minutes60: "1시간봉", minutes240: "4시간봉",
  days: "1일봉", weeks: "주봉", months: "월봉",
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
    if (chk("kMa1Filter"))    filter.push(`단기MA${val("kMa1Period")}`);
    if (chk("kMa2Filter"))    filter.push(`중기MA${val("kMa2Period")}`);
    if (chk("kMa3Filter"))    filter.push(`장기MA${val("kMa3Period")}`);
    if (chk("kVolumeFilter")) filter.push(`볼륨${val("kVolumeMult")}x`);
    return `진입: 시가+K(${k})×전봉변동폭 | 청산: ${exit.join(" · ")} | 필터: ${filter.length ? filter.join(" · ") : "없음"}`;
  }
  if (strategy === "RSI_DIVERGENCE_TRAIL") {
    const period  = val("rdiRsiPeriod");
    const lookback = val("rdiLookback");
    const vol     = val("rdiVolMult");
    const trail   = val("rdiTrailPct");
    const sl      = val("rdiSlPct");
    const filter  = [];
    if (chk("rdiMaFilter")) filter.push(`MA${val("rdiMaPeriod")}봉`);
    return `진입: RSI${period} 다이버전스 + 거래량${vol}x (탐색${lookback}봉) | 청산: 트레일${trail}% · SL-${sl}% | 필터: ${filter.length ? filter.join(" · ") : "없음"}`;
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
  if (strategy === "TRAILING_BREAKOUT") {
    const k     = val("tbKSlider");
    const sl    = val("tbSl");
    const trail = val("tbTrail");
    const filter = [];
    if (chk("tbMa1Filter"))    filter.push(`단기MA${val("tbMa1Period")}`);
    if (chk("tbMa2Filter"))    filter.push(`장기MA${val("tbMa2Period")}`);
    if (chk("tbVolumeFilter")) filter.push(`볼륨${val("tbVolumeMult")}x`);
    return `진입: 시가+K(${k})×전봉변동폭 | SL: -${sl}% 고정 · 트레일: 고점-${trail}% | 필터: ${filter.length ? filter.join(" · ") : "없음"}`;
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
  ["ctrl-k", "ctrl-tb", "ctrl-rdi", "ctrl-rsi", "ctrl-ma", "ctrl-bb"].forEach(id =>
    document.getElementById(id).classList.remove("active")
  );
  const map = {
    K_VOLATILITY_BREAKOUT: "ctrl-k",
    RSI_OVERSOLD_BOUNCE:   "ctrl-rsi",
    RSI_DIVERGENCE_TRAIL:  "ctrl-rdi",
    MA_GOLDEN_CROSS:       "ctrl-ma",
    BOLLINGER_BOUNCE:      "ctrl-bb",
    TRAILING_BREAKOUT:     "ctrl-tb",
  };
  const id = map[strategy];
  if (id) document.getElementById(id).classList.add("active");
  document.getElementById("strategyOverview").textContent = STRATEGY_OVERVIEW[strategy] || "";
  document.getElementById("strategyDesc").textContent = getStrategyDesc(strategy);
  document.getElementById("btResult").style.display = "none";
}

function updateStrategyDesc() {
  const strategy = document.getElementById("strategySelect").value;
  document.getElementById("strategyOverview").textContent = STRATEGY_OVERVIEW[strategy] || "";
  document.getElementById("strategyDesc").textContent = getStrategyDesc(strategy);
}

document.querySelectorAll(".param-panel input, .param-panel select").forEach(el => {
  el.addEventListener("input",  updateStrategyDesc);
  el.addEventListener("change", updateStrategyDesc);
});

const kSlider  = document.getElementById("kSlider");
const kDisplay = document.getElementById("kValueDisplay");
kSlider.addEventListener("input", () => { kDisplay.textContent = kSlider.value; });

const tbKSlider  = document.getElementById("tbKSlider");
const tbKDisplay = document.getElementById("tbKValueDisplay");
tbKSlider.addEventListener("input", () => { tbKDisplay.textContent = tbKSlider.value; });

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

async function runBacktest() {
  const market   = document.getElementById("marketSelect").value;
  if (!market) { showToast("마켓을 선택해주세요"); return; }
  const strategy = document.getElementById("strategySelect").value;
  const interval = document.getElementById("intervalSelect").value;
  const count    = parseInt(document.getElementById("candleCount").value) || 200;
  const initialCapital = getCapitalValue();

  let params = `market=${market}&strategy=${strategy}&interval=${interval}&count=${count}&initial_capital=${initialCapital}`;
  if (strategy === "RSI_DIVERGENCE_TRAIL") {
    params += `&rdi_rsi_period=${document.getElementById("rdiRsiPeriod").value}`;
    params += `&rdi_lookback=${document.getElementById("rdiLookback").value}`;
    params += `&rdi_vol_mult=${document.getElementById("rdiVolMult").value}`;
    params += `&rdi_trail_pct=${parseFloat(document.getElementById("rdiTrailPct").value) / 100}`;
    params += `&rdi_sl_pct=${-parseFloat(document.getElementById("rdiSlPct").value) / 100}`;
    params += `&rdi_ma_filter=${document.getElementById("rdiMaFilter").checked}`;
    params += `&rdi_ma_period=${document.getElementById("rdiMaPeriod").value}`;
  } else if (strategy === "TRAILING_BREAKOUT") {
    params += `&k=${parseFloat(document.getElementById("tbKSlider").value)}`;
    params += `&tb_sl=${-parseFloat(document.getElementById("tbSl").value) / 100}`;
    params += `&tb_trail=${parseFloat(document.getElementById("tbTrail").value) / 100}`;
    params += `&tb_ma1_filter=${document.getElementById("tbMa1Filter").checked}`;
    params += `&tb_ma1_period=${document.getElementById("tbMa1Period").value}`;
    params += `&tb_ma2_filter=${document.getElementById("tbMa2Filter").checked}`;
    params += `&tb_ma2_period=${document.getElementById("tbMa2Period").value}`;
    params += `&tb_volume_filter=${document.getElementById("tbVolumeFilter").checked}`;
    params += `&tb_volume_mult=${document.getElementById("tbVolumeMult").value}`;
  } else if (strategy === "K_VOLATILITY_BREAKOUT") {
    params += `&k=${parseFloat(kSlider.value)}`;
    params += `&k_use_tp=${document.getElementById("kUseTp").checked}`;
    params += `&k_tp=${parseFloat(document.getElementById("kTp").value) / 100}`;
    params += `&k_use_sl=${document.getElementById("kUseSl").checked}`;
    params += `&k_sl=${-parseFloat(document.getElementById("kSl").value) / 100}`;
    params += `&k_ma1_filter=${document.getElementById("kMa1Filter").checked}`;
    params += `&k_ma1_period=${document.getElementById("kMa1Period").value}`;
    params += `&k_ma2_filter=${document.getElementById("kMa2Filter").checked}`;
    params += `&k_ma2_period=${document.getElementById("kMa2Period").value}`;
    params += `&k_ma3_filter=${document.getElementById("kMa3Filter").checked}`;
    params += `&k_ma3_period=${document.getElementById("kMa3Period").value}`;
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
  document.getElementById("btErrorMsg").style.display = "none";

  try {
    const res  = await fetch(`/api/backtesting?${params}`);
    const data = await res.json();
    if (data.error) {
      showBtError(data.error);
      return;
    }
    document.getElementById("btResult").style.display = "block";
    renderBacktest(data);
  } catch (e) {
    showBtError("백테스팅 오류: " + e.message);
  } finally {
    btn.disabled = false;
    document.getElementById("btLoadingMsg").style.display = "none";
  }
}

function showBtError(message) {
  document.getElementById("btErrorText").textContent = message;
  document.getElementById("btErrorMsg").style.display = "block";
}
