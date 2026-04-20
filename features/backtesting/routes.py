from flask import Blueprint, jsonify, request
from .service import run_backtest

backtesting_bp = Blueprint("backtesting", __name__, url_prefix="/api")


@backtesting_bp.route("/backtesting")
def backtesting():
    exchange = request.args.get("exchange", "upbit")
    market = request.args.get("market", "KRW-BTC")
    strategy = request.args.get("strategy", "K_VOLATILITY_BREAKOUT")
    k = float(request.args.get("k", 0.5))
    k_tp = float(request.args.get("k_tp", 0.05))
    k_sl = float(request.args.get("k_sl", -0.03))
    k_use_tp = request.args.get("k_use_tp", "true").lower() == "true"
    k_use_sl = request.args.get("k_use_sl", "true").lower() == "true"
    k_ma_filter = request.args.get("k_ma_filter", "false").lower() == "true"
    k_ma_period = int(request.args.get("k_ma_period", 20))
    k_volume_filter = request.args.get("k_volume_filter", "false").lower() == "true"
    k_volume_mult = float(request.args.get("k_volume_mult", 1.5))
    rsi_period = int(request.args.get("rsi_period", 14))
    rsi_threshold = float(request.args.get("rsi_threshold", 30))
    rsi_exit = float(request.args.get("rsi_exit", 62))
    rsi_tp = float(request.args.get("rsi_tp", 0.07))
    rsi_sl = float(request.args.get("rsi_sl", -0.04))
    rsi_entry_mode = request.args.get("rsi_entry_mode", "crossover")
    rsi_ma_filter = request.args.get("rsi_ma_filter", "false").lower() == "true"
    rsi_ma_period = int(request.args.get("rsi_ma_period", 20))
    rsi_volume_filter = request.args.get("rsi_volume_filter", "false").lower() == "true"
    rsi_volume_mult = float(request.args.get("rsi_volume_mult", 1.5))
    rsi_use_tp = request.args.get("rsi_use_tp", "true").lower() == "true"
    rsi_use_sl = request.args.get("rsi_use_sl", "true").lower() == "true"
    rsi_use_rsi_exit = request.args.get("rsi_use_rsi_exit", "true").lower() == "true"
    rsi_max_hold_bars = int(request.args.get("rsi_max_hold_bars", 0))
    ma_fast = int(request.args.get("ma_fast", 5))
    ma_slow = int(request.args.get("ma_slow", 20))
    ma_use_tp = request.args.get("ma_use_tp", "true").lower() == "true"
    ma_tp = float(request.args.get("ma_tp", 0.05))
    ma_use_sl = request.args.get("ma_use_sl", "false").lower() == "true"
    ma_sl = float(request.args.get("ma_sl", -0.03))
    ma_use_ma_exit = request.args.get("ma_use_ma_exit", "true").lower() == "true"
    ma_volume_filter = request.args.get("ma_volume_filter", "false").lower() == "true"
    ma_volume_mult = float(request.args.get("ma_volume_mult", 1.5))
    ma_max_hold_bars = int(request.args.get("ma_max_hold_bars", 0))
    bb_period = int(request.args.get("bb_period", 20))
    bb_std = float(request.args.get("bb_std", 2.0))
    bb_use_tp = request.args.get("bb_use_tp", "true").lower() == "true"
    bb_tp = float(request.args.get("bb_tp", 0.05))
    bb_use_sl = request.args.get("bb_use_sl", "false").lower() == "true"
    bb_sl = float(request.args.get("bb_sl", -0.03))
    bb_use_middle_exit = request.args.get("bb_use_middle_exit", "true").lower() == "true"
    bb_volume_filter = request.args.get("bb_volume_filter", "false").lower() == "true"
    bb_volume_mult = float(request.args.get("bb_volume_mult", 1.5))
    bb_max_hold_bars = int(request.args.get("bb_max_hold_bars", 0))
    interval = request.args.get("interval", "days")
    count = int(request.args.get("count", 200))
    initial_capital = int(request.args.get("initial_capital", 1000000))

    return jsonify(run_backtest(
        exchange=exchange, market=market, strategy=strategy,
        k=k, k_tp=k_tp, k_sl=k_sl, k_use_tp=k_use_tp, k_use_sl=k_use_sl,
        k_ma_filter=k_ma_filter, k_ma_period=k_ma_period,
        k_volume_filter=k_volume_filter, k_volume_mult=k_volume_mult,
        rsi_period=rsi_period, rsi_threshold=rsi_threshold, rsi_exit=rsi_exit,
        rsi_tp=rsi_tp, rsi_sl=rsi_sl,
        rsi_entry_mode=rsi_entry_mode,
        rsi_ma_filter=rsi_ma_filter, rsi_ma_period=rsi_ma_period,
        rsi_volume_filter=rsi_volume_filter, rsi_volume_mult=rsi_volume_mult,
        rsi_use_tp=rsi_use_tp, rsi_use_sl=rsi_use_sl, rsi_use_rsi_exit=rsi_use_rsi_exit,
        rsi_max_hold_bars=rsi_max_hold_bars,
        ma_fast=ma_fast, ma_slow=ma_slow,
        ma_use_tp=ma_use_tp, ma_tp=ma_tp, ma_use_sl=ma_use_sl, ma_sl=ma_sl,
        ma_use_ma_exit=ma_use_ma_exit,
        ma_volume_filter=ma_volume_filter, ma_volume_mult=ma_volume_mult, ma_max_hold_bars=ma_max_hold_bars,
        bb_period=bb_period, bb_std=bb_std,
        bb_use_tp=bb_use_tp, bb_tp=bb_tp, bb_use_sl=bb_use_sl, bb_sl=bb_sl,
        bb_use_middle_exit=bb_use_middle_exit,
        bb_volume_filter=bb_volume_filter, bb_volume_mult=bb_volume_mult, bb_max_hold_bars=bb_max_hold_bars,
        interval=interval, count=count, initial_capital=initial_capital,
    ))
