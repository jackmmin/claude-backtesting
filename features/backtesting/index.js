const { getCandlesBulk } = require("../../exchanges/upbit/candles");

const MIN_CANDLES = 30;
const FEE_RATE = 0.0005;    // 매수/매도 각 0.05% 수수료
const TAKE_PROFIT = 0.05;   // 수익률 5% 도달 시 익절 청산

async function runBacktest({
  market = "KRW-BTC",
  strategy = "K_VOLATILITY_BREAKOUT",
  k = 0.5,
  rsiPeriod = 14, rsiThreshold = 30, rsiExit = 62, rsiTp = 0.07, rsiSl = -0.04,
  maFast = 5, maSlow = 20,
  bbPeriod = 20, bbStd = 2.0,
  interval = "days", count = 200, initialCapital = 1000000,
} = {}) {
  let candles;
  try {
    candles = await getCandlesBulk(market, count, interval);
  } catch (e) {
    return { error: `데이터를 가져오지 못했습니다. 네트워크 또는 업비트 API 오류: ${e.message}` };
  }
  if (!candles || candles.length === 0) {
    return { error: `데이터를 가져오지 못했습니다. (${market} ${interval} 캔들 0개 수신)` };
  }
  if (candles.length < MIN_CANDLES) {
    return { error: `데이터 부족: ${candles.length}개 수집 (최소 ${MIN_CANDLES}개 필요)` };
  }
  const data = [...candles].reverse();

  if (strategy === "K_VOLATILITY_BREAKOUT") {
    return kVolatilityBacktest(data, k, initialCapital);
  }
  if (strategy === "RSI_OVERSOLD_BOUNCE") return rsiOversoldBacktest(data, rsiPeriod, rsiThreshold, rsiExit, rsiTp, rsiSl, initialCapital);
  if (strategy === "MA_GOLDEN_CROSS") return maGoldenCrossBacktest(data, maFast, maSlow, initialCapital);
  if (strategy === "BOLLINGER_BOUNCE") return bollingerBounceBacktest(data, bbPeriod, bbStd, initialCapital);
  return { error: `알 수 없는 전략: ${strategy}` };
}

// ── K변동성 돌파 ──────────────────────────────────────────────────────────────

function kVolatilityBacktest(data, k, initialCapital) {
  const trades = [];
  let inTrade = false;
  let entryPrice = null; // 수수료 포함 매수 단가
  let tpPrice    = null;
  let entryDate  = null;
  let entryDatetime = null;

  for (let i = 1; i < data.length; i++) {
    const prev    = data[i - 1];
    const curr    = data[i];
    const currDate = curr.candle_date_time_kst.slice(0, 10);

    if (inTrade) {
      const isNewDay = currDate !== entryDate;

      if (curr.high_price >= tpPrice) {
        // TP 도달 → 즉시 익절
        const rawSell = tpPrice;
        const sell    = rawSell * (1 - FEE_RATE);
        const pnl     = (sell - entryPrice) / entryPrice;
        trades.push({ date: entryDate, buy_datetime: entryDatetime, sell_datetime: curr.candle_date_time_kst, buy_price: Math.round(entryPrice / (1 + FEE_RATE)), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
        inTrade = false;
      } else if (isNewDay) {
        // 당일 종료 → 전 캔들(당일 마지막) 종가로 청산
        const rawSell = prev.trade_price;
        const sell    = rawSell * (1 - FEE_RATE);
        const pnl     = (sell - entryPrice) / entryPrice;
        trades.push({ date: entryDate, buy_datetime: entryDatetime, sell_datetime: prev.candle_date_time_kst, buy_price: Math.round(entryPrice / (1 + FEE_RATE)), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
        inTrade = false;
        // 새 날 진입 신호 체크로 fall-through
      } else {
        continue; // 당일 보유 중 → 재진입 차단
      }
    }

    // 진입 신호 체크 (포지션 없을 때만)
    if (!inTrade) {
      const prevRange = prev.high_price - prev.low_price;
      if (prevRange <= 0) continue;
      const target = curr.opening_price + k * prevRange;
      if (curr.high_price >= target) {
        const buyCost = target * (1 + FEE_RATE);
        const tp      = target * (1 + TAKE_PROFIT);

        if (curr.high_price >= tp) {
          // 진입 캔들에서 바로 TP 달성
          const rawSell = tp;
          const sell    = rawSell * (1 - FEE_RATE);
          const pnl     = (sell - buyCost) / buyCost;
          trades.push({ date: currDate, buy_datetime: curr.candle_date_time_kst, sell_datetime: curr.candle_date_time_kst, buy_price: Math.round(target), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
        } else {
          // 당일 EOD까지 홀딩
          entryPrice    = buyCost;
          tpPrice       = tp;
          entryDate     = currDate;
          entryDatetime = curr.candle_date_time_kst;
          inTrade       = true;
        }
      }
    }
  }

  // 데이터 끝까지 포지션 보유 중이면 마지막 캔들 종가로 청산
  if (inTrade) {
    const last    = data[data.length - 1];
    const rawSell = last.trade_price;
    const sell    = rawSell * (1 - FEE_RATE);
    const pnl     = (sell - entryPrice) / entryPrice;
    trades.push({ date: entryDate, buy_datetime: entryDatetime, sell_datetime: last.candle_date_time_kst, buy_price: Math.round(entryPrice / (1 + FEE_RATE)), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
  }

  let currentSignal = null;
  if (data.length >= 2) {
    const prev     = data[data.length - 2];
    const curr     = data[data.length - 1];
    const prevRange = prev.high_price - prev.low_price;
    const target   = curr.opening_price + k * prevRange;
    currentSignal  = { date: curr.candle_date_time_kst.slice(0, 16), open: curr.opening_price, prev_range: Math.round(prevRange), target_price: Math.round(target), current_price: curr.trade_price, triggered: curr.high_price >= target, in_trade: inTrade, k };
  }
  return buildResult("K_VOLATILITY_BREAKOUT", trades, initialCapital, currentSignal, data, { k, total_candles: data.length });
}

// ── RSI 과매도 반등 ────────────────────────────────────────────────────────────
// 개선: RSI 회복 후 진입 · Wilder EMA · 손절 -4% · TP 7% · 20MA 추세 필터

function rsiOversoldBacktest(data, period, threshold, exitThreshold, takeProfit, stopLoss, initialCapital) {
  const trades = [];
  let inTrade = false, entryPrice = null, entryDate = null, entryDatetime = null;
  for (let i = period + 1; i < data.length; i++) {
    const closes = data.slice(0, i + 1).map(c => c.trade_price);
    const rsiCurr = calcRsi(closes, period);
    const rsiPrev = calcRsi(closes.slice(0, -1), period);
    if (rsiCurr === null || rsiPrev === null) continue;

    if (!inTrade) {
      // 진입: RSI가 threshold 아래에서 위로 회복 크로스
      if (rsiCurr >= threshold && rsiPrev < threshold) {
        if (i + 1 < data.length) {
          entryPrice = data[i + 1].opening_price * (1 + FEE_RATE);
          entryDate = data[i].candle_date_time_kst.slice(0, 10);
          entryDatetime = data[i + 1].candle_date_time_kst;
          inTrade = true;
        }
    } else {
      const rawEntry = entryPrice / (1 + FEE_RATE);
      const tpPrice = rawEntry * (1 + takeProfit);
      const slPrice = rawEntry * (1 + stopLoss);

      if (data[i].high_price >= tpPrice) {
        const rawSell = tpPrice;
        const sell = rawSell * (1 - FEE_RATE);
        const pnl = (sell - entryPrice) / entryPrice;
        trades.push({ date: entryDate, buy_datetime: entryDatetime, sell_datetime: data[i].candle_date_time_kst, buy_price: Math.round(rawEntry), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
        inTrade = false;
      } else if (data[i].low_price <= slPrice) {
        const rawSell = slPrice;
        const sell = rawSell * (1 - FEE_RATE);
        const pnl = (sell - entryPrice) / entryPrice;
        trades.push({ date: entryDate, buy_datetime: entryDatetime, sell_datetime: data[i].candle_date_time_kst, buy_price: Math.round(rawEntry), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
        inTrade = false;
      } else if (rsiCurr >= exitThreshold) {
        if (i + 1 < data.length) {
          const rawSell = data[i + 1].opening_price;
          const sell = rawSell * (1 - FEE_RATE);
          const pnl = (sell - entryPrice) / entryPrice;
          trades.push({ date: entryDate, buy_datetime: entryDatetime, sell_datetime: data[i + 1].candle_date_time_kst, buy_price: Math.round(rawEntry), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
          inTrade = false;
        }
      }
    }
  }

  const closes = data.map(c => c.trade_price);
  const rsiCurr = calcRsi(closes, period);
  const rsiPrev = calcRsi(closes.slice(0, -1), period);
  const currentSignal = {
    date: data[data.length - 1].candle_date_time_kst.slice(0, 10),
    rsi_value: rsiCurr !== null ? Math.round(rsiCurr * 100) / 100 : null,
    threshold, exit_threshold: exitThreshold,
    triggered: rsiCurr !== null && rsiPrev !== null && rsiCurr >= threshold && rsiPrev < threshold,
    in_trade: inTrade,
  };
  return buildResult("RSI_OVERSOLD_BOUNCE", trades, initialCapital, currentSignal, data,
    { rsi_period: period, rsi_threshold: threshold, rsi_exit: exitThreshold, rsi_tp: takeProfit, rsi_sl: stopLoss, total_candles: data.length });
}

// ── MA 골든크로스 ──────────────────────────────────────────────────────────────

function maGoldenCrossBacktest(data, fast, slow, initialCapital) {
  const trades = [];
  let inTrade = false, entryPrice = null, entryDate = null, entryDatetime = null;

  for (let i = slow + 1; i < data.length; i++) {
    const closes = data.slice(0, i + 1).map(c => c.trade_price);
    const prev = closes.slice(0, -1);
    const maFastCurr = calcSma(closes, fast), maSlowCurr = calcSma(closes, slow);
    const maFastPrev = calcSma(prev, fast), maSlowPrev = calcSma(prev, slow);
    if ([maFastCurr, maSlowCurr, maFastPrev, maSlowPrev].includes(null)) continue;

    if (!inTrade) {
      if (maFastPrev <= maSlowPrev && maFastCurr > maSlowCurr) {
        if (i + 1 < data.length) { entryPrice = data[i + 1].opening_price * (1 + FEE_RATE); entryDate = data[i].candle_date_time_kst.slice(0, 10); entryDatetime = data[i + 1].candle_date_time_kst; inTrade = true; }
      }
    } else {
      const tpPrice = (entryPrice / (1 + FEE_RATE)) * (1 + TAKE_PROFIT);
      if (data[i].high_price >= tpPrice) {
        // TP 도달: 해당 봉 고가 기준 익절 청산
        const rawSell = tpPrice;
        const sell = rawSell * (1 - FEE_RATE);
        const pnl = (sell - entryPrice) / entryPrice;
        trades.push({ date: entryDate, buy_datetime: entryDatetime, sell_datetime: data[i].candle_date_time_kst, buy_price: Math.round(entryPrice / (1 + FEE_RATE)), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
        inTrade = false;
      } else if (maFastPrev >= maSlowPrev && maFastCurr < maSlowCurr) {
        if (i + 1 < data.length) {
          const rawSell = data[i + 1].opening_price;
          const sell = rawSell * (1 - FEE_RATE);  // 매도 수수료 반영
          const pnl = (sell - entryPrice) / entryPrice;
          trades.push({ date: entryDate, buy_datetime: entryDatetime, sell_datetime: data[i + 1].candle_date_time_kst, buy_price: Math.round(entryPrice / (1 + FEE_RATE)), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
          inTrade = false;
        }
      }
    }
  }

  const closes = data.map(c => c.trade_price);
  const maFastVal = calcSma(closes, fast), maSlowVal = calcSma(closes, slow);
  const maFastPrev = calcSma(closes.slice(0, -1), fast), maSlowPrev = calcSma(closes.slice(0, -1), slow);
  const goldenCross = maFastPrev !== null && maSlowPrev !== null && maFastVal !== null && maSlowVal !== null && maFastPrev <= maSlowPrev && maFastVal > maSlowVal;
  const currentSignal = {
    date: data[data.length - 1].candle_date_time_kst.slice(0, 10),
    ma_fast: maFastVal !== null ? Math.round(maFastVal) : null,
    ma_slow: maSlowVal !== null ? Math.round(maSlowVal) : null,
    fast_period: fast, slow_period: slow,
    triggered: goldenCross, in_trade: inTrade,
  };
  return buildResult("MA_GOLDEN_CROSS", trades, initialCapital, currentSignal, data, { ma_fast: fast, ma_slow: slow, total_candles: data.length });
}

// ── 볼린저밴드 반등 ────────────────────────────────────────────────────────────

function bollingerBounceBacktest(data, period, stdMult, initialCapital) {
  const trades = [];
  let inTrade = false, entryPrice = null, entryDate = null, entryDatetime = null;

  for (let i = period + 1; i < data.length; i++) {
    const closes = data.slice(0, i + 1).map(c => c.trade_price);
    const last = closes.slice(-period);
    if (last.length < 2) continue;
    const middle = last.reduce((a, b) => a + b, 0) / period;
    const std = calcStd(last);
    const lower = middle - stdMult * std;
    const curr = closes[closes.length - 1], prev = closes[closes.length - 2];

    if (!inTrade) {
      if (prev < lower && curr >= lower) {
        if (i + 1 < data.length) { entryPrice = data[i + 1].opening_price * (1 + FEE_RATE); entryDate = data[i].candle_date_time_kst.slice(0, 10); entryDatetime = data[i + 1].candle_date_time_kst; inTrade = true; }
      }
    } else {
      const tpPrice = (entryPrice / (1 + FEE_RATE)) * (1 + TAKE_PROFIT);
      if (data[i].high_price >= tpPrice) {
        // TP 도달: 해당 봉 고가 기준 익절 청산
        const rawSell = tpPrice;
        const sell = rawSell * (1 - FEE_RATE);
        const pnl = (sell - entryPrice) / entryPrice;
        trades.push({ date: entryDate, buy_datetime: entryDatetime, sell_datetime: data[i].candle_date_time_kst, buy_price: Math.round(entryPrice / (1 + FEE_RATE)), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
        inTrade = false;
      } else if (curr >= middle) {
        if (i + 1 < data.length) {
          const rawSell = data[i + 1].opening_price;
          const sell = rawSell * (1 - FEE_RATE);  // 매도 수수료 반영
          const pnl = (sell - entryPrice) / entryPrice;
          trades.push({ date: entryDate, buy_datetime: entryDatetime, sell_datetime: data[i + 1].candle_date_time_kst, buy_price: Math.round(entryPrice / (1 + FEE_RATE)), sell_price: Math.round(rawSell), pnl: Math.round(pnl * 1e6) / 1e6, win: pnl > 0 });
          inTrade = false;
        }
      }
    }
  }

  const closes = data.map(c => c.trade_price);
  const last = closes.slice(-period);
  const middle = last.reduce((a, b) => a + b, 0) / last.length;
  const std = calcStd(last);
  const lower = middle - stdMult * std, upper = middle + stdMult * std;
  const currentSignal = {
    date: data[data.length - 1].candle_date_time_kst.slice(0, 10),
    current_price: closes[closes.length - 1],
    lower_band: Math.round(lower), middle_band: Math.round(middle), upper_band: Math.round(upper),
    triggered: closes.length >= 2 && closes[closes.length - 2] < lower && closes[closes.length - 1] >= lower,
    in_trade: inTrade,
  };
  return buildResult("BOLLINGER_BOUNCE", trades, initialCapital, currentSignal, data, { bb_period: period, bb_std: stdMult, total_candles: data.length });
}

// ── 공통 결과 빌더 ─────────────────────────────────────────────────────────────

function buildResult(strategy, trades, initialCapital, currentSignal, candles = [], extra = {}) {
  const candleData = candles.map(c => ({
    t: c.candle_date_time_kst,
    o: c.opening_price,
    h: c.high_price,
    l: c.low_price,
    c: c.trade_price,
  }));

  const base = { strategy, total_trades: 0, win_rate: 0, avg_pnl_per_trade: 0, total_return: 0, initial_capital: initialCapital, final_value: initialCapital, profit_loss: 0, equity_curve: [], current_signal: currentSignal, trades: [], candles: candleData, trade_markers: [], ...extra };
  if (!trades.length) return base;

  const wins = trades.filter(t => t.win).length;
  let portfolio = initialCapital;
  const equityCurve = [];
  for (const t of trades) {
    const prev = portfolio;
    portfolio = Math.round(portfolio * (1 + t.pnl));
    equityCurve.push({ date: t.date, value: portfolio });
    t.krw_pnl = portfolio - prev;
    t.entry_amount = prev;
    // 청산 완료 시 매수+매도 수수료, 보유중(미청산)은 매수 수수료만
    t.fee = Math.round(prev * FEE_RATE * (t.sell_datetime ? 2 : 1));
  }

  const tradeMarkers = trades
    .filter(t => t.buy_datetime && t.sell_datetime)
    .map(t => ({ buy_datetime: t.buy_datetime, sell_datetime: t.sell_datetime, win: t.win }));

  return {
    ...base,
    total_trades: trades.length,
    win_rate: Math.round((wins / trades.length) * 1e4) / 1e4,
    avg_pnl_per_trade: Math.round((trades.reduce((s, t) => s + t.pnl, 0) / trades.length) * 1e6) / 1e6,
    total_return: Math.round((portfolio / initialCapital - 1) * 1e4) / 1e4,
    final_value: portfolio,
    profit_loss: portfolio - initialCapital,
    equity_curve: equityCurve,
    trades: trades.slice(-50),
    trade_markers: tradeMarkers,
  };
}

// ── 유틸 ──────────────────────────────────────────────────────────────────────

function calcSma(values, period) {
  if (values.length < period) return null;
  return values.slice(-period).reduce((a, b) => a + b, 0) / period;
}

function calcRsi(closes, period = 14) {
  if (closes.length < period + 1) return null;
  const diffs = [];
  for (let i = 1; i < closes.length; i++) diffs.push(closes[i] - closes[i - 1]);
  const gains = diffs.map(d => Math.max(d, 0));
  const losses = diffs.map(d => Math.abs(Math.min(d, 0)));
  // Wilder EMA: SMA 시드 후 지수 스무딩
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = period; i < gains.length; i++) {
    avgGain = (avgGain * (period - 1) + gains[i]) / period;
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
  }
  if (avgLoss === 0) return avgGain > 0 ? 100 : 50;
  return 100 - 100 / (1 + avgGain / avgLoss);
}

function calcStd(values) {
  if (values.length < 2) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0) / (values.length - 1);
  return Math.sqrt(variance);
}

module.exports = { runBacktest };
