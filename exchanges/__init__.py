from exchanges import upbit as _upbit

_registry = {"upbit": _upbit}


def get_exchange(name="upbit"):
    exchange = _registry.get(name)
    if not exchange:
        raise ValueError(f"Unknown exchange: {name}")
    return exchange
