const { fetchUpbit } = require("./client");

async function getMarkets() {
  const allMarkets = await fetchUpbit("/market/all?isDetails=false");
  const krwMarkets = allMarkets.filter((m) => m.market.startsWith("KRW-"));
  const marketCodes = krwMarkets.map((m) => m.market).join(",");
  const tickers = await fetchUpbit(`/ticker?markets=${marketCodes}`);
  tickers.sort((a, b) => b.acc_trade_price_24h - a.acc_trade_price_24h);
  const top10Codes = new Set(tickers.slice(0, 10).map((t) => t.market));
  return krwMarkets.filter((m) => top10Codes.has(m.market));
}

module.exports = { getMarkets };
