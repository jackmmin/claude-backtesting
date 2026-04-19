from datetime import datetime, timedelta
from .client import get

INTERVAL_PATH = {
    "minutes15":  "/candles/minutes/15",
    "minutes60":  "/candles/minutes/60",
    "minutes240": "/candles/minutes/240",
    "days":       "/candles/days",
    "weeks":      "/candles/weeks",
    "months":     "/candles/months",
}


def get_candles(market="KRW-BTC", count=90):
    return get("/candles/days", params={"market": market, "count": count})


def get_candles_bulk(market="KRW-BTC", count=200, interval="days"):
    path = INTERVAL_PATH.get(interval, "/candles/days")
    count = min(count, 400)

    batch1 = get(path, params={"market": market, "count": min(count, 200)})
    if len(batch1) < 200 or count <= 200:
        return batch1

    oldest_dt = datetime.strptime(batch1[-1]["candle_date_time_utc"], "%Y-%m-%dT%H:%M:%S")
    to_str = (oldest_dt - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S")

    batch2 = get(path, params={
        "market": market,
        "count": min(count - 200, 200),
        "to": to_str,
    })

    return batch1 + batch2
