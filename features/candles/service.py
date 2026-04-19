from exchanges import get_exchange


def get_candles(exchange="upbit", market="KRW-BTC", count=90, interval="days"):
    return get_exchange(exchange).get_candles_bulk(market, count=int(count), interval=interval)
