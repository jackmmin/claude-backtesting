const { fetchUpbit } = require("./client");

const INTERVAL_PATH = {
  minutes15:  "/candles/minutes/15",
  minutes60:  "/candles/minutes/60",
  minutes240: "/candles/minutes/240",
  days:       "/candles/days",
  weeks:      "/candles/weeks",
  months:     "/candles/months",
};

async function getCandles(market = "KRW-BTC", count = 90) {
  return fetchUpbit(`/candles/days?market=${market}&count=${count}`);
}

async function getCandlesBulk(market = "KRW-BTC", count = 200, interval = "days") {
  const path = INTERVAL_PATH[interval] || "/candles/days";
  count = Math.min(count, 1000);

  const result = [];
  let remaining = count;
  let toParam = "";

  while (remaining > 0) {
    const batchSize = Math.min(remaining, 200);
    const url = toParam
      ? `${path}?market=${market}&count=${batchSize}&to=${toParam}`
      : `${path}?market=${market}&count=${batchSize}`;
    const batch = await fetchUpbit(url);
    if (!batch.length) break;
    result.push(...batch);
    remaining -= batch.length;
    if (batch.length < batchSize) break;
    const oldest = batch[batch.length - 1];
    const oldestDt = new Date(oldest.candle_date_time_utc + "Z");
    oldestDt.setSeconds(oldestDt.getSeconds() - 1);
    toParam = oldestDt.toISOString().replace(".000Z", "");
  }

  return result;
}

module.exports = { getCandles, getCandlesBulk };
