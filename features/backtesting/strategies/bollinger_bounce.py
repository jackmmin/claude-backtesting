import statistics as stats
from .utils import FEE_RATE, build_result


def run(data, period=20, std_mult=2.0, initial_capital=1000000,
        bb_use_tp=True, bb_tp=0.05,
        bb_use_sl=False, bb_sl=-0.03,
        bb_use_middle_exit=True,
        bb_volume_filter=False, bb_volume_mult=1.5,
        bb_max_hold_bars=0):
    trades = []
    portfolio = initial_capital
    in_trade = False
    entry_price = None
    entry_date = None
    entry_datetime = None
    entry_amount = None  # 진입 시점 포트폴리오 스냅샷
    hold_bars = 0

    for i in range(period + 1, len(data)):
        closes = [c["trade_price"] for c in data[:i + 1]]
        last = closes[-period:]
        if len(last) < 2:
            continue

        middle = sum(last) / period
        std = stats.stdev(last)
        lower = middle - std_mult * std

        curr_close = closes[-1]
        prev_close = closes[-2]

        if not in_trade:
            if prev_close < lower and curr_close >= lower:
                if bb_volume_filter:
                    vol_window = data[max(0, i - 20):i]
                    vols = [c.get("candle_acc_trade_volume", 0) for c in vol_window]
                    avg_vol = sum(vols) / len(vol_window) if vol_window else 0
                    curr_vol = data[i].get("candle_acc_trade_volume", 0)
                    if avg_vol > 0 and curr_vol < avg_vol * bb_volume_mult:
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
            tp_price = raw_entry * (1 + bb_tp)
            sl_price = raw_entry * (1 + bb_sl)
            exited_sell = None
            exited_dt = data[i]["candle_date_time_kst"]

            if bb_use_tp and data[i]["high_price"] >= tp_price:
                exited_sell = tp_price
            elif bb_use_sl and data[i]["low_price"] <= sl_price:
                exited_sell = sl_price
            elif bb_use_middle_exit and curr_close >= middle:
                if i + 1 < len(data):
                    exited_sell = data[i + 1]["opening_price"]
            elif bb_max_hold_bars > 0 and hold_bars >= bb_max_hold_bars:
                exited_sell = data[i]["trade_price"]

            if exited_sell is not None:
                sell_price = exited_sell * (1 - FEE_RATE)
                pnl = (sell_price - entry_price) / entry_price
                portfolio = round(portfolio * (1 + pnl))
                trades.append({
                    "date": entry_date,
                    "buy_datetime": entry_datetime,
                    "sell_datetime": exited_dt,
                    "buy_price": raw_entry,
                    "sell_price": exited_sell,
                    "pnl": round(pnl, 6),
                    "win": pnl > 0,
                    "entry_amount": entry_amount,
                    "fee": round(entry_amount * FEE_RATE * 2),
                })
                in_trade = False

    open_trade = None
    if in_trade and entry_price is not None:
        current_price = data[-1]["trade_price"]
        raw_entry = entry_price / (1 + FEE_RATE)
        pnl_unrealized = (current_price * (1 - FEE_RATE) - entry_price) / entry_price
        open_trade = {
            "date": entry_date,
            "buy_datetime": entry_datetime,
            "sell_datetime": "",
            "buy_price": raw_entry,
            "sell_price": current_price,
            "pnl": round(pnl_unrealized, 6),
            "win": pnl_unrealized > 0,
            "open": True,
        }

    closes = [c["trade_price"] for c in data]
    last = closes[-period:] if len(closes) >= period else closes
    middle = sum(last) / len(last)
    std = stats.stdev(last) if len(last) >= 2 else 0
    lower = middle - std_mult * std
    upper = middle + std_mult * std
    bounce = len(closes) >= 2 and closes[-2] < lower and closes[-1] >= lower

    # 마지막 캔들에서 반등 신호 발생 시 진입 예정 포지션을 보유중으로 표시
    if not in_trade and bounce:
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
        }

    current_signal = {
        "date": data[-1]["candle_date_time_kst"][:10],
        "current_price": closes[-1],
        "lower_band": round(lower),
        "middle_band": round(middle),
        "upper_band": round(upper),
        "triggered": bounce,
        "in_trade": in_trade,
    }

    return build_result("BOLLINGER_BOUNCE", trades, initial_capital, current_signal,
                        open_trade=open_trade,
                        candles=data, bb_period=period, bb_std=std_mult,
                        bb_use_tp=bb_use_tp, bb_tp=bb_tp, bb_use_sl=bb_use_sl, bb_sl=bb_sl,
                        bb_use_middle_exit=bb_use_middle_exit,
                        bb_volume_filter=bb_volume_filter, bb_volume_mult=bb_volume_mult,
                        bb_max_hold_bars=bb_max_hold_bars,
                        total_candles=len(data))
