from datetime import datetime, timedelta
from .client import get


def get_candles(market="KRW-BTC", count=90):
    return get("/candles/days", params={"market": market, "count": count})


def get_candles_bulk(market="KRW-BTC", count=365):
    """Fetch up to 400 daily candles using pagination (Upbit limit: 200 per request)."""
    count = min(count, 400)

    batch1 = get("/candles/days", params={"market": market, "count": min(count, 200)})
    if len(batch1) < 200 or count <= 200:
        return batch1

    oldest_dt = datetime.strptime(batch1[-1]["candle_date_time_utc"], "%Y-%m-%dT%H:%M:%S")
    to_str = (oldest_dt - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")

    batch2 = get("/candles/days", params={
        "market": market,
        "count": min(count - 200, 200),
        "to": to_str,
    })

    return batch1 + batch2
