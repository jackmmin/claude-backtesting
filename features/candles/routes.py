from flask import Blueprint, jsonify, request, make_response
from .service import get_candles

candles_bp = Blueprint("candles", __name__, url_prefix="/api")


@candles_bp.route("/candles")
def candles():
    exchange = request.args.get("exchange", "upbit")
    market = request.args.get("market", "KRW-BTC")
    count = int(request.args.get("count", 90))
    interval = request.args.get("interval", "days")
    data = get_candles(exchange, market, count, interval)
    resp = make_response(jsonify(data))
    # 분봉은 5분, 일봉 이상은 60초 캐시
    ttl = 300 if interval.startswith("minutes") else 60
    resp.headers["Cache-Control"] = f"public, max-age={ttl}"
    return resp
