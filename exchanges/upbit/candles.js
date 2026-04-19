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
  count = Math.min(count, 400);

  const batch1 = await fetchUpbit(`${path}?market=${market}&count=${Math.min(count, 200)}`);
  if (batch1.length < 200 || count <= 200) return batch1;

  const oldest = batch1[batch1.length - 1];
  const oldestDt = new Date(oldest.candle_date_time_utc + "Z");
  oldestDt.setSeconds(oldestDt.getSeconds() - 1);
  const toStr = oldestDt.toISOString().replace(".000Z", "");

  const batch2 = await fetchUpbit(
    `${path}?market=${market}&count=${Math.min(count - 200, 200)}&to=${toStr}`
  );

  return [...batch1, ...batch2];
}

module.exports = { getCandles, getCandlesBulk };
