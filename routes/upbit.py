from flask import Blueprint, jsonify, request
from api.upbit.markets import get_markets
from api.upbit.candles import get_candles
from api.upbit.ticker import get_ticker

upbit_bp = Blueprint("upbit", __name__, url_prefix="/api")


@upbit_bp.route("/markets")
def markets():
    return jsonify(get_markets())


@upbit_bp.route("/candles")
def candles():
    market = request.args.get("market", "KRW-BTC")
    count = request.args.get("count", 90)
    return jsonify(get_candles(market, count))


@upbit_bp.route("/ticker")
def ticker():
    market = request.args.get("market", "KRW-BTC")
    return jsonify(get_ticker(market))
