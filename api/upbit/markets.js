const { fetchUpbit } = require("./client");

async function getMarkets() {
  const data = await fetchUpbit("/market/all?isDetails=false");
  return data.filter((m) => m.market.startsWith("KRW-"));
}

module.exports = { getMarkets };
