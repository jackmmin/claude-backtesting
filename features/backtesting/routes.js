const { runBacktest } = require("./index");

async function handle(req, res, query) {
  const market = query.market || "KRW-BTC";
  const strategy = query.strategy || "K_VOLATILITY_BREAKOUT";
  const k = parseFloat(query.k || 0.5);
  const rsiPeriod = parseInt(query.rsi_period || 14);
  const rsiThreshold = parseFloat(query.rsi_threshold || 30);
  const rsiExit = parseFloat(query.rsi_exit || 50);
  const maFast = parseInt(query.ma_fast || 5);
  const maSlow = parseInt(query.ma_slow || 20);
  const bbPeriod = parseInt(query.bb_period || 20);
  const bbStd = parseFloat(query.bb_std || 2.0);
  const interval = query.interval || "days";
  const count = parseInt(query.count || 200);
  const initialCapital = parseInt(query.initial_capital || 1000000);

  const data = await runBacktest({
    market, strategy, k, rsiPeriod, rsiThreshold, rsiExit,
    maFast, maSlow, bbPeriod, bbStd, interval, count, initialCapital,
  });
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(data));
}

module.exports = { path: "/api/backtesting", handle };
