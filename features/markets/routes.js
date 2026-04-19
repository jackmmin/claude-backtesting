const { getMarkets } = require("./index");

async function handle(req, res, query) {
  const data = await getMarkets(query.exchange);
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(data));
}

module.exports = { path: "/api/markets", handle };
