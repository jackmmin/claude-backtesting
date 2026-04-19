const { getCandlesBulk } = require("../../exchanges/upbit/candles");

const MIN_CANDLES = { days: 365 };

async function runBacktest({ market = "KRW-BTC", k = 0.5, interval = "days" } = {}) {
  const minRequired = MIN_CANDLES[interval] || 365;
  const candles = await getCandlesBulk(market, minRequired);

  if (candles.length < minRequired) {
    return { error: `데이터 부족: ${candles.length}개 수집 (최소 ${minRequired}개 필요)` };
  }

  return kVolatilityBacktest(candles, k);
}

function kVolatilityBacktest(candles, k) {
  // Upbit returns newest-first; reverse to chronological order
  const data = [...candles].reverse();

  const trades = [];
  for (let i = 1; i < data.length - 1; i++) {
    const prev = data[i - 1];
    const curr = data[i];
    const nextDay = data[i + 1];

    const prevRange = prev.high_price - prev.low_price;
    if (prevRange <= 0) continue;

    const target = curr.opening_price + k * prevRange;

    if (curr.high_price >= target) {
      const sell = nextDay.opening_price;
      const pnl = (sell - target) / target;
      trades.push({
        date: curr.candle_date_time_kst.slice(0, 10),
        buy_price: Math.round(target),
        sell_price: Math.round(sell),
        pnl: Math.round(pnl * 1e6) / 1e6,
        win: pnl > 0,
      });
    }
  }

  let currentSignal = null;
  if (data.length >= 2) {
    const prev = data[data.length - 2];
    const curr = data[data.length - 1];
    const prevRange = prev.high_price - prev.low_price;
    const target = curr.opening_price + k * prevRange;
    currentSignal = {
      date: curr.candle_date_time_kst.slice(0, 10),
      open: curr.opening_price,
      prev_range: Math.round(prevRange),
      target_price: Math.round(target),
      current_price: curr.trade_price,
      triggered: curr.high_price >= target,
      k,
    };
  }

  if (!trades.length) {
    return {
      strategy: "K_VOLATILITY_BREAKOUT", k,
      total_candles: data.length, total_trades: 0,
      win_rate: 0, avg_pnl_per_trade: 0, total_return: 0,
      current_signal: currentSignal, trades: [],
    };
  }

  const wins = trades.filter((t) => t.win).length;
  const winRate = wins / trades.length;
  const avgPnl = trades.reduce((s, t) => s + t.pnl, 0) / trades.length;
  const cumulative = trades.reduce((s, t) => s * (1 + t.pnl), 1);

  return {
    strategy: "K_VOLATILITY_BREAKOUT",
    k,
    total_candles: data.length,
    total_trades: trades.length,
    win_rate: Math.round(winRate * 1e4) / 1e4,
    avg_pnl_per_trade: Math.round(avgPnl * 1e6) / 1e6,
    total_return: Math.round((cumulative - 1) * 1e4) / 1e4,
    current_signal: currentSignal,
    trades: trades.slice(-30),
  };
}

module.exports = { runBacktest };
