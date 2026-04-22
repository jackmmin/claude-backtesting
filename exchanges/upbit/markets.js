const { fetchUpbit } = require("./client");

async function getMarkets() {
  const allMarkets = await fetchUpbit("/market/all?isDetails=false");
  const krwMarkets = allMarkets.filter((m) => m.market.startsWith("KRW-"));
  const marketCodes = krwMarkets.map((m) => m.market).join(",");
  const tickers = await fetchUpbit(`/ticker?markets=${marketCodes}`);
  tickers.sort((a, b) => b.acc_trade_price_24h - a.acc_trade_price_24h);
  const marketMap = Object.fromEntries(krwMarkets.map((m) => [m.market, m]));
  return tickers.slice(0, 20).filter((t) => marketMap[t.market]).map((t) => marketMap[t.market]);
}

module.exports = { getMarkets };
