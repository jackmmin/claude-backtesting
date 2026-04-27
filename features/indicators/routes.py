from flask import Blueprint, jsonify, request, make_response
from .service import get_indicators

indicators_bp = Blueprint("indicators", __name__, url_prefix="/api")


@indicators_bp.route("/indicators")
def indicators():
    exchange = request.args.get("exchange", "upbit")
    market   = request.args.get("market", "KRW-BTC")
    count    = min(int(request.args.get("count", 200)), 1000)
    interval = request.args.get("interval", "days")
    data = get_indicators(exchange, market, count, interval)
    resp = make_response(jsonify(data))
    # 분봉은 5분, 일봉 이상은 60초 캐시
    ttl = 300 if interval.startswith("minutes") else 60
    resp.headers["Cache-Control"] = f"public, max-age={ttl}"
    return resp
