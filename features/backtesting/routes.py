from flask import Blueprint, jsonify, request
from .service import run_backtest

backtesting_bp = Blueprint("backtesting", __name__, url_prefix="/api")


@backtesting_bp.route("/backtesting")
def backtesting():
    exchange = request.args.get("exchange", "upbit")
    market = request.args.get("market", "KRW-BTC")
    k = float(request.args.get("k", 0.5))
    interval = request.args.get("interval", "days")
    count = int(request.args.get("count", 200))
    initial_capital = int(request.args.get("initial_capital", 1000000))
    return jsonify(run_backtest(exchange, market, k, interval, count, initial_capital))
