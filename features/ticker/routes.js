const { getTicker } = require("./index");

async function handle(req, res, query) {
  const data = await getTicker(query.exchange, query.market);
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(data));
}

module.exports = { path: "/api/ticker", handle };
