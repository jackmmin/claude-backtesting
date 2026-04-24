import logging
from flask import Blueprint, jsonify, request
from .service import run_backtest

backtesting_bp = Blueprint("backtesting", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


def _f(key, default):
    """쿼리 파라미터를 float으로 변환. 실패 시 default 반환."""
    try:
        return float(request.args.get(key, default))
    except (ValueError, TypeError):
        return float(default)


def _i(key, default):
    """쿼리 파라미터를 int으로 변환. 실패 시 default 반환."""
    try:
        return int(request.args.get(key, default))
    except (ValueError, TypeError):
        return int(default)


def _b(key, default="false"):
    """쿼리 파라미터를 bool으로 변환."""
    return request.args.get(key, default).lower() == "true"


@backtesting_bp.route("/backtesting")
def backtesting():
    try:
        exchange        = request.args.get("exchange", "upbit")
        market          = request.args.get("market", "KRW-BTC")
        strategy        = request.args.get("strategy", "K_VOLATILITY_BREAKOUT")
        interval        = request.args.get("interval", "days")
        rsi_entry_mode  = request.args.get("rsi_entry_mode", "crossover")

        result = run_backtest(
            exchange=exchange, market=market, strategy=strategy,
            k=_f("k", 0.5),
            tb_sl=_f("tb_sl", -0.02), tb_trail=_f("tb_trail", 0.03),
            tb_ma1_filter=_b("tb_ma1_filter"), tb_ma1_period=_i("tb_ma1_period", 20),
            tb_ma2_filter=_b("tb_ma2_filter"), tb_ma2_period=_i("tb_ma2_period", 60),
            tb_volume_filter=_b("tb_volume_filter"), tb_volume_mult=_f("tb_volume_mult", 1.5),
            k_tp=_f("k_tp", 0.05), k_sl=_f("k_sl", -0.03),
            k_use_tp=_b("k_use_tp", "true"), k_use_sl=_b("k_use_sl", "true"),
            k_ma1_filter=_b("k_ma1_filter"), k_ma1_period=_i("k_ma1_period", 5),
            k_ma2_filter=_b("k_ma2_filter"), k_ma2_period=_i("k_ma2_period", 20),
            k_ma3_filter=_b("k_ma3_filter"), k_ma3_period=_i("k_ma3_period", 60),
            k_volume_filter=_b("k_volume_filter"), k_volume_mult=_f("k_volume_mult", 1.5),
            rsi_period=_i("rsi_period", 14), rsi_threshold=_f("rsi_threshold", 30),
            rsi_exit=_f("rsi_exit", 62), rsi_tp=_f("rsi_tp", 0.07), rsi_sl=_f("rsi_sl", -0.04),
            rsi_entry_mode=rsi_entry_mode,
            rsi_ma_filter=_b("rsi_ma_filter"), rsi_ma_period=_i("rsi_ma_period", 20),
            rsi_volume_filter=_b("rsi_volume_filter"), rsi_volume_mult=_f("rsi_volume_mult", 1.5),
            rsi_use_tp=_b("rsi_use_tp", "true"), rsi_use_sl=_b("rsi_use_sl", "true"),
            rsi_use_rsi_exit=_b("rsi_use_rsi_exit", "true"),
            rsi_max_hold_bars=_i("rsi_max_hold_bars", 0),
            ma_fast=_i("ma_fast", 5), ma_slow=_i("ma_slow", 20),
            ma_use_tp=_b("ma_use_tp", "true"), ma_tp=_f("ma_tp", 0.05),
            ma_use_sl=_b("ma_use_sl"), ma_sl=_f("ma_sl", -0.03),
            ma_use_ma_exit=_b("ma_use_ma_exit", "true"),
            ma_volume_filter=_b("ma_volume_filter"), ma_volume_mult=_f("ma_volume_mult", 1.5),
            ma_max_hold_bars=_i("ma_max_hold_bars", 0),
            bb_period=_i("bb_period", 20), bb_std=_f("bb_std", 2.0),
            bb_use_tp=_b("bb_use_tp", "true"), bb_tp=_f("bb_tp", 0.05),
            bb_use_sl=_b("bb_use_sl"), bb_sl=_f("bb_sl", -0.03),
            bb_use_middle_exit=_b("bb_use_middle_exit", "true"),
            bb_volume_filter=_b("bb_volume_filter"), bb_volume_mult=_f("bb_volume_mult", 1.5),
            bb_max_hold_bars=_i("bb_max_hold_bars", 0),
            rdi_rsi_period=_i("rdi_rsi_period", 14), rdi_lookback=_i("rdi_lookback", 30),
            rdi_vol_mult=_f("rdi_vol_mult", 1.5), rdi_trail_pct=_f("rdi_trail_pct", 0.03),
            rdi_sl_pct=_f("rdi_sl_pct", -0.03),
            rdi_ma_filter=_b("rdi_ma_filter"), rdi_ma_period=_i("rdi_ma_period", 60),
            interval=interval, count=_i("count", 200), initial_capital=_i("initial_capital", 1000000),
        )
        return jsonify(result)
    except Exception as e:
        logger.error("백테스팅 오류", exc_info=True)
        return jsonify({"error": f"백테스팅 처리 중 오류가 발생했습니다: {e}"}), 500
