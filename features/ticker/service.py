from exchanges import get_exchange


def get_ticker(exchange="upbit", market="KRW-BTC"):
    return get_exchange(exchange).get_ticker(market)
