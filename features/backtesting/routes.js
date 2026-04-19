const { runBacktest } = require("./index");

async function handle(req, res, query) {
  const market = query.market || "KRW-BTC";
  const k = parseFloat(query.k || 0.5);
  const interval = query.interval || "days";

  const data = await runBacktest({ market, k, interval });
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(data));
}

module.exports = { path: "/api/backtesting", handle };
