from flask import Blueprint, jsonify, request
from .service import run_backtest

backtesting_bp = Blueprint("backtesting", __name__, url_prefix="/api")


@backtesting_bp.route("/backtesting")
def backtesting():
    exchange = request.args.get("exchange", "upbit")
    market = request.args.get("market", "KRW-BTC")
    strategy = request.args.get("strategy", "K_VOLATILITY_BREAKOUT")
    k = float(request.args.get("k", 0.5))
    rsi_period = int(request.args.get("rsi_period", 14))
    rsi_threshold = float(request.args.get("rsi_threshold", 30))
    rsi_exit = float(request.args.get("rsi_exit", 50))
    ma_fast = int(request.args.get("ma_fast", 5))
    ma_slow = int(request.args.get("ma_slow", 20))
    bb_period = int(request.args.get("bb_period", 20))
    bb_std = float(request.args.get("bb_std", 2.0))
    interval = request.args.get("interval", "days")
    count = int(request.args.get("count", 200))
    initial_capital = int(request.args.get("initial_capital", 1000000))

    return jsonify(run_backtest(
        exchange=exchange, market=market, strategy=strategy,
        k=k, rsi_period=rsi_period, rsi_threshold=rsi_threshold, rsi_exit=rsi_exit,
        ma_fast=ma_fast, ma_slow=ma_slow, bb_period=bb_period, bb_std=bb_std,
        interval=interval, count=count, initial_capital=initial_capital,
    ))
