from .utils import FEE_RATE, sma, rsi, build_result


def run(data, period=14, threshold=30, exit_threshold=62,
        take_profit=0.07, stop_loss=-0.04, initial_capital=1000000,
        entry_mode="crossover",
        rsi_ma_filter=False, rsi_ma_period=20,
        rsi_volume_filter=False, rsi_volume_mult=1.0,
        use_tp=True, use_sl=True, use_rsi_exit=True,
        max_hold_bars=0):
    trades = []
    portfolio = initial_capital
    in_trade = False
    entry_price = None
    entry_date = None
    entry_datetime = None
    entry_amount = None  # 진입 시점 포트폴리오 스냅샷
    hold_bars = 0

    for i in range(period + 1, len(data)):
        closes_curr = [c["trade_price"] for c in data[:i + 1]]
        closes_prev = closes_curr[:-1]

        rsi_curr = rsi(closes_curr, period)
        rsi_prev = rsi(closes_prev, period)

        if rsi_curr is None or rsi_prev is None:
            continue

        if not in_trade:
            # 진입 방식 선택
            if entry_mode == "crossover":
                # RSI가 과매도 임계값 아래에서 위로 회복 크로스
                triggered = rsi_curr >= threshold and rsi_prev < threshold
            else:
                # immediate: RSI가 과매도 임계값 아래로 최초 하락 시 즉시 진입
                triggered = rsi_curr < threshold and rsi_prev >= threshold

            if triggered and i + 1 < len(data):
                # MA 추세 필터: 현재 종가가 MA 아래면 진입 제외
                if rsi_ma_filter:
                    ma = sma(closes_curr, rsi_ma_period)
                    if ma is not None and closes_curr[-1] < ma:
                        continue
                # 볼륨 필터: 당일 거래량이 최근 평균 × 배수 미만이면 진입 제외
                if rsi_volume_filter:
                    vol_window = data[max(0, i - 20):i]
                    vols = [c.get("candle_acc_trade_volume", 0) for c in vol_window]
                    avg_vol = sum(vols) / len(vol_window) if vol_window else 0
                    curr_vol = data[i].get("candle_acc_trade_volume", 0)
                    if avg_vol > 0 and curr_vol < avg_vol * rsi_volume_mult:
                        continue

                entry_price = data[i + 1]["opening_price"] * (1 + FEE_RATE)
                entry_date = data[i]["candle_date_time_kst"][:10]
                entry_datetime = data[i + 1]["candle_date_time_kst"]
                entry_amount = portfolio
                in_trade = True
                hold_bars = 0
        else:
            hold_bars += 1
            raw_entry = entry_price / (1 + FEE_RATE)
            tp_price = raw_entry * (1 + take_profit)
            sl_price = raw_entry * (1 + stop_loss)

            exited_sell = None
            exited_dt = data[i]["candle_date_time_kst"]

            if use_tp and data[i]["high_price"] >= tp_price:
                exited_sell = tp_price
            elif use_sl and data[i]["low_price"] <= sl_price:
                exited_sell = sl_price
            elif use_rsi_exit and rsi_curr >= exit_threshold and i + 1 < len(data):
                exited_sell = data[i + 1]["opening_price"]
            elif max_hold_bars > 0 and hold_bars >= max_hold_bars:
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
            "date": entry_date,
            "buy_datetime": entry_datetime,
            "sell_datetime": "",
            "buy_price": raw_entry,
            "sell_price": current_price,
            "pnl": round(pnl_unrealized, 6),
            "win": pnl_unrealized > 0,
            "open": True,
            "entry_amount": entry_amount,
            "fee": round(entry_amount * FEE_RATE),  # 진입 수수료만 (청산 전)
        }

    closes = [c["trade_price"] for c in data]
    rsi_curr = rsi(closes, period)
    rsi_prev = rsi(closes[:-1], period)
    if entry_mode == "crossover":
        sig_triggered = (rsi_curr is not None and rsi_prev is not None
                         and rsi_curr >= threshold and rsi_prev < threshold)
    else:
        sig_triggered = (rsi_curr is not None and rsi_prev is not None
                         and rsi_curr < threshold and rsi_prev >= threshold)

    # 마지막 캔들에서 신호 발생 시 진입 예정 포지션을 보유중으로 표시
    if not in_trade and sig_triggered:
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
        "rsi_value": round(rsi_curr, 2) if rsi_curr is not None else None,
        "threshold": threshold,
        "exit_threshold": exit_threshold,
        "entry_mode": entry_mode,
        "triggered": sig_triggered,
        "in_trade": in_trade,
    }

    return build_result("RSI_OVERSOLD_BOUNCE", trades, initial_capital, current_signal,
                        open_trade=open_trade,
                        candles=data, rsi_period=period, rsi_threshold=threshold,
                        rsi_exit=exit_threshold, rsi_tp=take_profit, rsi_sl=stop_loss,
                        entry_mode=entry_mode,
                        rsi_ma_filter=rsi_ma_filter, rsi_ma_period=rsi_ma_period,
                        rsi_volume_filter=rsi_volume_filter, rsi_volume_mult=rsi_volume_mult,
                        use_tp=use_tp, use_sl=use_sl, use_rsi_exit=use_rsi_exit,
                        max_hold_bars=max_hold_bars,
                        total_candles=len(data))
