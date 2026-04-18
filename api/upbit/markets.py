from .client import get


def get_markets():
    data = get("/market/all", params={"isDetails": "false"})
    return [m for m in data if m["market"].startswith("KRW-")]
