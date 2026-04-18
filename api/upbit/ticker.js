const { fetchUpbit } = require("./client");

async function getTicker(market = "KRW-BTC") {
  return fetchUpbit(`/ticker?markets=${market}`);
}

module.exports = { getTicker };
