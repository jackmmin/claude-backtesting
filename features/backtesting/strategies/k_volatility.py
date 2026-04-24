from .utils import FEE_RATE, sma, build_result


def run(data, k=0.5, initial_capital=1000000,
        k_tp=0.05, k_sl=-0.03, k_use_tp=True, k_use_sl=True,
        k_ma1_filter=False, k_ma1_period=5,
        k_ma2_filter=False, k_ma2_period=20,
        k_ma3_filter=False, k_ma3_period=60,
        k_volume_filter=False, k_volume_mult=1.5):
    trades = []
    portfolio = initial_capital
    last_trade_date = None  # 하루 1회 거래 제한 (분봉 사용 시 동일 날짜 중복 진입 방지)
    ma_configs = [
        (k_ma1_filter, k_ma1_period),
        (k_ma2_filter, k_ma2_period),
        (k_ma3_filter, k_ma3_period),
    ]
    for i in range(1, len(data)):
        prev = data[i - 1]
        curr = data[i]
        curr_date = curr["candle_date_time_kst"][:10]

        # 같은 날 이미 거래가 발생했으면 건너뜀
        if last_trade_date == curr_date:
            continue

        # 활성화된 모든 MA 추세 필터 통과 시 진입 (시가가 각 MA 위에 있어야 함)
        skip = False
        closes_i = [c["trade_price"] for c in data[:i]]
        for enabled, period in ma_configs:
            if not enabled:
                continue
            if i < period:
                skip = True
                break
            ma = sma(closes_i, period)
            if ma is not None and curr["opening_price"] < ma:
                skip = True
                break
        if skip:
            continue

        # 볼륨 필터: 당일 거래량이 최근 20일 평균 × 배수 미만이면 진입 제외
        if k_volume_filter:
            vol_window = data[max(0, i - 20):i]
            vols = [c.get("candle_acc_trade_volume", 0) for c in vol_window]
            avg_vol = sum(vols) / len(vol_window) if vol_window else 0
            curr_vol = curr.get("candle_acc_trade_volume", 0)
            if avg_vol > 0 and curr_vol < avg_vol * k_volume_mult:
                continue

        prev_range = prev["high_price"] - prev["low_price"]
        if prev_range <= 0:
            continue

        target = curr["opening_price"] + k * prev_range
        if curr["high_price"] >= target:
            buy_cost = target * (1 + FEE_RATE)
            tp_price = target * (1 + k_tp)
            sl_price = target * (1 + k_sl)

            if k_use_tp and curr["high_price"] >= tp_price:
                raw_sell = tp_price
            elif k_use_sl and curr["low_price"] <= sl_price:
                raw_sell = sl_price
            else:
                raw_sell = curr["trade_price"]

            sell = raw_sell * (1 - FEE_RATE)
            pnl = (sell - buy_cost) / buy_cost
            entry_amount = portfolio  # 진입 시점 포트폴리오 전액 투자
            portfolio = round(portfolio * (1 + pnl))  # 잔고 갱신
            last_trade_date = curr_date  # 당일 추가 진입 방지
            exit_amount = round(entry_amount * (1 + pnl))
            trades.append({
                "date": curr["candle_date_time_kst"][:16],
                "buy_datetime": curr["candle_date_time_kst"],
                "sell_datetime": curr["candle_date_time_kst"][:10] + " 23:50:00",
                "buy_price": target,
                "sell_price": raw_sell,
                "pnl": round(pnl, 6),
                "win": pnl > 0,
                "entry_amount": entry_amount,
                "fee": round(entry_amount * FEE_RATE + exit_amount * FEE_RATE),
            })

    current_signal = None
    if len(data) >= 2:
        prev = data[-2]
        curr = data[-1]
        prev_range = prev["high_price"] - prev["low_price"]
        target = curr["opening_price"] + k * prev_range
        current_signal = {
            "date": curr["candle_date_time_kst"][:16],
            "open": curr["opening_price"],
            "prev_range": round(prev_range),
            "target_price": round(target),
            "current_price": curr["trade_price"],
            "triggered": curr["high_price"] >= target,
            "in_trade": False,
            "k": k,
        }

    return build_result("K_VOLATILITY_BREAKOUT", trades, initial_capital, current_signal,
                        candles=data, k=k, k_tp=k_tp, k_sl=k_sl,
                        k_use_tp=k_use_tp, k_use_sl=k_use_sl,
                        k_ma1_filter=k_ma1_filter, k_ma1_period=k_ma1_period,
                        k_ma2_filter=k_ma2_filter, k_ma2_period=k_ma2_period,
                        k_ma3_filter=k_ma3_filter, k_ma3_period=k_ma3_period,
                        k_volume_filter=k_volume_filter, k_volume_mult=k_volume_mult,
                        total_candles=len(data))
