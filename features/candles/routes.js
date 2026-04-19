const { getCandles } = require("./index");

async function handle(req, res, query) {
  const data = await getCandles(query.exchange, query.market, query.count);
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(data));
}

module.exports = { path: "/api/candles", handle };
