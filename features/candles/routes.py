from flask import Blueprint, jsonify, request
from .service import get_candles

candles_bp = Blueprint("candles", __name__, url_prefix="/api")


@candles_bp.route("/candles")
def candles():
    exchange = request.args.get("exchange", "upbit")
    market = request.args.get("market", "KRW-BTC")
    count = request.args.get("count", 90)
    return jsonify(get_candles(exchange, market, count))
