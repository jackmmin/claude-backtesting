from exchanges import get_exchange
from .strategies import k_volatility, rsi_oversold, ma_golden_cross, bollinger_bounce, trailing_breakout


def run_backtest(
    exchange="upbit", market="KRW-BTC",
    strategy="K_VOLATILITY_BREAKOUT",
    k=0.5,
    tb_sl=-0.02, tb_trail=0.03,
    tb_ma1_filter=False, tb_ma1_period=20,
    tb_ma2_filter=False, tb_ma2_period=60,
    tb_volume_filter=False, tb_volume_mult=1.5,
    k_tp=0.05, k_sl=-0.03, k_use_tp=True, k_use_sl=True,
    k_ma1_filter=False, k_ma1_period=5,
    k_ma2_filter=False, k_ma2_period=20,
    k_ma3_filter=False, k_ma3_period=60,
    k_volume_filter=False, k_volume_mult=1.5,
    rsi_period=14, rsi_threshold=30, rsi_exit=62, rsi_tp=0.07, rsi_sl=-0.04,
    rsi_entry_mode="crossover",
    rsi_ma_filter=False, rsi_ma_period=20,
    rsi_volume_filter=False, rsi_volume_mult=1.0,
    rsi_use_tp=True, rsi_use_sl=True, rsi_use_rsi_exit=True,
    rsi_max_hold_bars=0,
    ma_fast=5, ma_slow=20,
    ma_use_tp=True, ma_tp=0.05, ma_use_sl=False, ma_sl=-0.03,
    ma_use_ma_exit=True, ma_volume_filter=False, ma_volume_mult=1.5, ma_max_hold_bars=0,
    bb_period=20, bb_std=2.0,
    bb_use_tp=True, bb_tp=0.05, bb_use_sl=False, bb_sl=-0.03,
    bb_use_middle_exit=True, bb_volume_filter=False, bb_volume_mult=1.5, bb_max_hold_bars=0,
    interval="days", count=200, initial_capital=1000000,
):
    exch = get_exchange(exchange)
    candles = exch.get_candles_bulk(market, count=count, interval=interval)

    if len(candles) < 2:
        return {"error": f"데이터 부족: {len(candles)}개 수집 (최소 2개 필요)"}

    data = list(reversed(candles))

    if strategy == "TRAILING_BREAKOUT":
        return trailing_breakout.run(data, k=k, initial_capital=initial_capital,
                                     tb_sl=tb_sl, tb_trail=tb_trail,
                                     tb_ma1_filter=tb_ma1_filter, tb_ma1_period=tb_ma1_period,
                                     tb_ma2_filter=tb_ma2_filter, tb_ma2_period=tb_ma2_period,
                                     tb_volume_filter=tb_volume_filter, tb_volume_mult=tb_volume_mult)
    if strategy == "K_VOLATILITY_BREAKOUT":
        return k_volatility.run(data, k=k, initial_capital=initial_capital,
                                k_tp=k_tp, k_sl=k_sl, k_use_tp=k_use_tp, k_use_sl=k_use_sl,
                                k_ma1_filter=k_ma1_filter, k_ma1_period=k_ma1_period,
                                k_ma2_filter=k_ma2_filter, k_ma2_period=k_ma2_period,
                                k_ma3_filter=k_ma3_filter, k_ma3_period=k_ma3_period,
                                k_volume_filter=k_volume_filter, k_volume_mult=k_volume_mult)
    if strategy == "RSI_OVERSOLD_BOUNCE":
        return rsi_oversold.run(data, period=rsi_period, threshold=rsi_threshold,
                                exit_threshold=rsi_exit, take_profit=rsi_tp,
                                stop_loss=rsi_sl, initial_capital=initial_capital,
                                entry_mode=rsi_entry_mode,
                                rsi_ma_filter=rsi_ma_filter, rsi_ma_period=rsi_ma_period,
                                rsi_volume_filter=rsi_volume_filter, rsi_volume_mult=rsi_volume_mult,
                                use_tp=rsi_use_tp, use_sl=rsi_use_sl, use_rsi_exit=rsi_use_rsi_exit,
                                max_hold_bars=rsi_max_hold_bars)
    if strategy == "MA_GOLDEN_CROSS":
        return ma_golden_cross.run(data, fast=ma_fast, slow=ma_slow, initial_capital=initial_capital,
                                   ma_use_tp=ma_use_tp, ma_tp=ma_tp, ma_use_sl=ma_use_sl, ma_sl=ma_sl,
                                   ma_use_ma_exit=ma_use_ma_exit,
                                   ma_volume_filter=ma_volume_filter, ma_volume_mult=ma_volume_mult,
                                   ma_max_hold_bars=ma_max_hold_bars)
    if strategy == "BOLLINGER_BOUNCE":
        return bollinger_bounce.run(data, period=bb_period, std_mult=bb_std, initial_capital=initial_capital,
                                    bb_use_tp=bb_use_tp, bb_tp=bb_tp, bb_use_sl=bb_use_sl, bb_sl=bb_sl,
                                    bb_use_middle_exit=bb_use_middle_exit,
                                    bb_volume_filter=bb_volume_filter, bb_volume_mult=bb_volume_mult,
                                    bb_max_hold_bars=bb_max_hold_bars)
    return {"error": f"알 수 없는 전략: {strategy}"}
