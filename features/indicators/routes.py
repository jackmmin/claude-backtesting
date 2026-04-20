from flask import Blueprint, jsonify, request
from .service import get_indicators

indicators_bp = Blueprint("indicators", __name__, url_prefix="/api")


@indicators_bp.route("/indicators")
def indicators():
    exchange = request.args.get("exchange", "upbit")
    market   = request.args.get("market", "KRW-BTC")
    count    = min(int(request.args.get("count", 200)), 1000)
    interval = request.args.get("interval", "days")
    return jsonify(get_indicators(exchange, market, count, interval))
