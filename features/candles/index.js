const { getExchange } = require("../../exchanges");

async function getCandles(exchange = "upbit", market = "KRW-BTC", count = 90) {
  return getExchange(exchange).getCandles(market, count);
}

module.exports = { getCandles };
