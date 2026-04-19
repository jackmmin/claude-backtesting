from .client import get


def get_markets():
    all_markets = get("/market/all", params={"isDetails": "false"})
    krw_markets = [m for m in all_markets if m["market"].startswith("KRW-")]
    market_codes = ",".join(m["market"] for m in krw_markets)
    tickers = get("/ticker", params={"markets": market_codes})
    tickers.sort(key=lambda t: t["acc_trade_price_24h"], reverse=True)
    top10_codes = {t["market"] for t in tickers[:10]}
    return [m for m in krw_markets if m["market"] in top10_codes]
