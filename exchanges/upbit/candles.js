const { fetchUpbit } = require("./client");

async function getCandles(market = "KRW-BTC", count = 90) {
  return fetchUpbit(`/candles/days?market=${market}&count=${count}`);
}

module.exports = { getCandles };
