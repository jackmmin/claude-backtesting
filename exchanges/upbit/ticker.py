from .client import get


def get_ticker(market="KRW-BTC"):
    return get("/ticker", params={"markets": market})
