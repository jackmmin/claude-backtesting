const { getMarkets } = require("../api/upbit/markets");
const { getCandles } = require("../api/upbit/candles");
const { getTicker } = require("../api/upbit/ticker");

async function handleUpbitRoutes(req, res, pathname, query) {
  if (pathname === "/api/markets") {
    const data = await getMarkets();
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify(data));
  }

  if (pathname === "/api/candles") {
    const data = await getCandles(query.market, query.count);
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify(data));
  }

  if (pathname === "/api/ticker") {
    const data = await getTicker(query.market);
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify(data));
  }

  return false;
}

module.exports = { handleUpbitRoutes };
