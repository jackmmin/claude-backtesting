from exchanges import get_exchange


def get_candles(exchange="upbit", market="KRW-BTC", count=90):
    return get_exchange(exchange).get_candles(market, count)
