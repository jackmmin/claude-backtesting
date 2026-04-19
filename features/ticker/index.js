const { getExchange } = require("../../exchanges");

async function getTicker(exchange = "upbit", market = "KRW-BTC") {
  return getExchange(exchange).getTicker(market);
}

module.exports = { getTicker };
