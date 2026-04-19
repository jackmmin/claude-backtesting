const { fetchUpbit } = require("./client");

async function getCandles(market = "KRW-BTC", count = 90) {
  return fetchUpbit(`/candles/days?market=${market}&count=${count}`);
}

async function getCandlesBulk(market = "KRW-BTC", count = 365) {
  count = Math.min(count, 400);

  const batch1 = await fetchUpbit(`/candles/days?market=${market}&count=${Math.min(count, 200)}`);
  if (batch1.length < 200 || count <= 200) return batch1;

  const oldest = batch1[batch1.length - 1];
  const oldestDt = new Date(oldest.candle_date_time_utc + "Z");
  oldestDt.setDate(oldestDt.getDate() - 1);
  const toStr = oldestDt.toISOString().replace(".000Z", "");

  const batch2 = await fetchUpbit(
    `/candles/days?market=${market}&count=${Math.min(count - 200, 200)}&to=${toStr}`
  );

  return [...batch1, ...batch2];
}

module.exports = { getCandles, getCandlesBulk };
