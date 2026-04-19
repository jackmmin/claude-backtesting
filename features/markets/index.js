const { getExchange } = require("../../exchanges");

async function getMarkets(exchange = "upbit") {
  return getExchange(exchange).getMarkets();
}

module.exports = { getMarkets };
