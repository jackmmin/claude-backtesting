from .client import get


def get_candles(market="KRW-BTC", count=90):
    return get("/candles/days", params={"market": market, "count": count})
