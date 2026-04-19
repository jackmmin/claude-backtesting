from exchanges import get_exchange


def get_markets(exchange="upbit"):
    return get_exchange(exchange).get_markets()
