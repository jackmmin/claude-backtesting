from flask import Blueprint, jsonify, request
from .service import calculate_signals

signals_bp = Blueprint("signals", __name__, url_prefix="/api")


@signals_bp.route("/signals")
def signals():
    exchange = request.args.get("exchange", "upbit")
    market = request.args.get("market", "KRW-BTC")
    count = min(int(request.args.get("count", 200)), 1000)
    interval = request.args.get("interval", "days")
    return jsonify(calculate_signals(exchange, market, count, interval))
