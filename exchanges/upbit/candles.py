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
    count = min(count, 1000)

    result = []
    remaining = count
    to_str = None

    while remaining > 0:
        batch_size = min(remaining, 200)
        params = {"market": market, "count": batch_size}
        if to_str:
            params["to"] = to_str
        batch = get(path, params=params)
        if not batch:
            break
        result.extend(batch)
        remaining -= len(batch)
        if len(batch) < batch_size:
            break
        oldest_dt = datetime.strptime(batch[-1]["candle_date_time_utc"], "%Y-%m-%dT%H:%M:%S")
        to_str = (oldest_dt - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S")

    return result
