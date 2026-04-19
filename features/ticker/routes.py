from flask import Blueprint, jsonify, request
from .service import get_ticker

ticker_bp = Blueprint("ticker", __name__, url_prefix="/api")


@ticker_bp.route("/ticker")
def ticker():
    exchange = request.args.get("exchange", "upbit")
    market = request.args.get("market", "KRW-BTC")
    return jsonify(get_ticker(exchange, market))
