from .utils import FEE_RATE, sma, build_result


def run(data, fast=5, slow=20, initial_capital=1000000,
        ma_use_tp=True, ma_tp=0.05,
        ma_use_sl=False, ma_sl=-0.03,
        ma_use_ma_exit=True,
        ma_volume_filter=False, ma_volume_mult=1.5,
        ma_max_hold_bars=0):
    trades = []
    portfolio = initial_capital
    in_trade = False
    entry_price = None
    entry_date = None
    entry_datetime = None
    entry_amount = None  # 진입 시점 포트폴리오 스냅샷
    hold_bars = 0

    for i in range(slow + 1, len(data)):
        closes_curr = [c["trade_price"] for c in data[:i + 1]]
        closes_prev = closes_curr[:-1]

        ma_fast_curr = sma(closes_curr, fast)
        ma_slow_curr = sma(closes_curr, slow)
        ma_fast_prev = sma(closes_prev, fast)
        ma_slow_prev = sma(closes_prev, slow)

        if None in (ma_fast_curr, ma_slow_curr, ma_fast_prev, ma_slow_prev):
            continue

        if not in_trade:
            if ma_fast_prev <= ma_slow_prev and ma_fast_curr > ma_slow_curr:
                if ma_volume_filter:
                    vol_window = data[max(0, i - 20):i]
                    vols = [c.get("candle_acc_trade_volume", 0) for c in vol_window]
                    avg_vol = sum(vols) / len(vol_window) if vol_window else 0
                    curr_vol = data[i].get("candle_acc_trade_volume", 0)
                    if avg_vol > 0 and curr_vol < avg_vol * ma_volume_mult:
                        continue
                if i + 1 < len(data):
                    entry_price = data[i + 1]["opening_price"] * (1 + FEE_RATE)
                    entry_date = data[i]["candle_date_time_kst"][:10]
                    entry_datetime = data[i + 1]["candle_date_time_kst"]
                    entry_amount = portfolio
                    in_trade = True
                    hold_bars = 0
        else:
            hold_bars += 1
            raw_entry = entry_price / (1 + FEE_RATE)
            tp_price = raw_entry * (1 + ma_tp)
            sl_price = raw_entry * (1 + ma_sl)
            exited_sell = None
            exited_dt = data[i]["candle_date_time_kst"]

            if ma_use_tp and data[i]["high_price"] >= tp_price:
                exited_sell = tp_price
            elif ma_use_sl and data[i]["low_price"] <= sl_price:
                exited_sell = sl_price
            elif ma_use_ma_exit and ma_fast_prev >= ma_slow_prev and ma_fast_curr < ma_slow_curr:
                if i + 1 < len(data):
                    exited_sell = data[i + 1]["opening_price"]
            elif ma_max_hold_bars > 0 and hold_bars >= ma_max_hold_bars:
                exited_sell = data[i]["trade_price"]

            if exited_sell is not None:
                sell_price = exited_sell * (1 - FEE_RATE)
                pnl = (sell_price - entry_price) / entry_price
                portfolio = round(portfolio * (1 + pnl))
                exit_amount = round(entry_amount * (1 + pnl))
                trades.append({
                    "date": entry_date,
                    "buy_datetime": entry_datetime,
                    "sell_datetime": exited_dt,
                    "buy_price": raw_entry,
                    "sell_price": exited_sell,
                    "pnl": round(pnl, 6),
                    "win": pnl > 0,
                    "entry_amount": entry_amount,
                    "fee": round(entry_amount * FEE_RATE + exit_amount * FEE_RATE),
                })
                in_trade = False

    open_trade = None
    if in_trade and entry_price is not None:
        current_price = data[-1]["trade_price"]
        raw_entry = entry_price / (1 + FEE_RATE)
        pnl_unrealized = (current_price * (1 - FEE_RATE) - entry_price) / entry_price
        exit_amount_unreal = round(entry_amount * (1 + pnl_unrealized))
        open_trade = {
            "date": entry_date, "buy_datetime": entry_datetime, "sell_datetime": "",
            "buy_price": raw_entry, "sell_price": current_price,
            "pnl": round(pnl_unrealized, 6), "win": pnl_unrealized > 0, "open": True,
            "entry_amount": entry_amount,
            "fee": round(entry_amount * FEE_RATE),  # 진입 수수료만 (청산 전)
        }

    closes = [c["trade_price"] for c in data]
    ma_fast_val = sma(closes, fast)
    ma_slow_val = sma(closes, slow)
    ma_fast_prev = sma(closes[:-1], fast)
    ma_slow_prev = sma(closes[:-1], slow)
    golden_cross = (
        ma_fast_prev is not None and ma_slow_prev is not None
        and ma_fast_val is not None and ma_slow_val is not None
        and ma_fast_prev <= ma_slow_prev and ma_fast_val > ma_slow_val
    )

    # 마지막 캔들에서 골든크로스 발생 시 진입 예정 포지션을 보유중으로 표시
    if not in_trade and golden_cross:
        cp = data[-1]["trade_price"]
        open_trade = {
            "date": data[-1]["candle_date_time_kst"][:10],
            "buy_datetime": data[-1]["candle_date_time_kst"],
            "sell_datetime": "",
            "buy_price": cp,
            "sell_price": cp,
            "pnl": 0.0,
            "win": False,
            "open": True,
            "entry_amount": portfolio,
            "fee": round(portfolio * FEE_RATE),  # 진입 수수료만 (청산 전)
        }

    current_signal = {
        "date": data[-1]["candle_date_time_kst"][:10],
        "ma_fast": round(ma_fast_val) if ma_fast_val is not None else None,
        "ma_slow": round(ma_slow_val) if ma_slow_val is not None else None,
        "fast_period": fast,
        "slow_period": slow,
        "triggered": golden_cross,
        "in_trade": in_trade,
    }

    return build_result("MA_GOLDEN_CROSS", trades, initial_capital, current_signal,
                        open_trade=open_trade,
                        candles=data, ma_fast=fast, ma_slow=slow,
                        ma_use_tp=ma_use_tp, ma_tp=ma_tp, ma_use_sl=ma_use_sl, ma_sl=ma_sl,
                        ma_use_ma_exit=ma_use_ma_exit,
                        ma_volume_filter=ma_volume_filter, ma_volume_mult=ma_volume_mult,
                        ma_max_hold_bars=ma_max_hold_bars,
                        total_candles=len(data))
