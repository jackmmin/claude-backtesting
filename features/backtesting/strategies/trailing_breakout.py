from .utils import FEE_RATE, sma, build_result


def run(data, k=0.5, initial_capital=1000000,
        tb_sl=-0.02, tb_trail=0.03,
        tb_ma1_filter=False, tb_ma1_period=20,
        tb_ma2_filter=False, tb_ma2_period=60,
        tb_volume_filter=False, tb_volume_mult=1.5):
    """
    변동성 돌파 진입 + 타이트 고정 손절 + 트레일링 스탑 익절
    - 진입: 시가 + K × 전일 변동폭 돌파 시 매수
    - 손절: 진입가 대비 tb_sl% (즉시 고정, 손실 제한)
    - 트레일링: 고점 대비 tb_trail% 하락 시 청산 (수익 극대화)
    - 하루 1거래 제한 (일봉 기준)
    """
    trades = []
    portfolio = initial_capital
    last_trade_date = None

    ma_configs = [
        (tb_ma1_filter, tb_ma1_period),
        (tb_ma2_filter, tb_ma2_period),
    ]

    for i in range(1, len(data)):
        prev = data[i - 1]
        curr = data[i]
        curr_date = curr["candle_date_time_kst"][:10]

        if last_trade_date == curr_date:
            continue

        # MA 추세 필터: 시가가 각 MA 위에 있어야 진입
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

        # 볼륨 필터: 당일 거래량이 최근 20봉 평균 × 배수 미만이면 제외
        if tb_volume_filter:
            vol_window = data[max(0, i - 20):i]
            vols = [c.get("candle_acc_trade_volume", 0) for c in vol_window]
            avg_vol = sum(vols) / len(vol_window) if vol_window else 0
            curr_vol = curr.get("candle_acc_trade_volume", 0)
            if avg_vol > 0 and curr_vol < avg_vol * tb_volume_mult:
                continue

        prev_range = prev["high_price"] - prev["low_price"]
        if prev_range <= 0:
            continue

        target = curr["opening_price"] + k * prev_range
        if curr["high_price"] < target:
            continue  # 당일 목표가 미돌파

        buy_cost = target * (1 + FEE_RATE)
        sl_price = target * (1 + tb_sl)          # 고정 손절가
        trail_gap = target * tb_trail             # 트레일링 갭 (절대값)

        # 캔들 내 고점/저점으로 청산 시뮬레이션
        # 진입 후 고점을 갱신하며 트레일링, 저점이 트레일 또는 손절에 닿으면 청산
        high_after_entry = target                 # 진입 후 최고점
        raw_sell = curr["trade_price"]            # 기본 청산가 = 당일 종가

        curr_high = curr["high_price"]
        curr_low  = curr["low_price"]

        # 고점 갱신 후 트레일 스탑 적용 (캔들 내 보수적 시뮬레이션)
        high_after_entry = max(high_after_entry, curr_high)
        trail_stop = high_after_entry - trail_gap

        if curr_low <= sl_price:
            # 손절 먼저 (타이트한 손실 제한)
            raw_sell = sl_price
        elif curr_low <= trail_stop and trail_stop > target:
            # 트레일링 스탑 (수익 구간에서만 작동)
            raw_sell = trail_stop
        # else: 당일 종가로 마감

        sell = raw_sell * (1 - FEE_RATE)
        pnl = (sell - buy_cost) / buy_cost
        entry_amount = portfolio  # 진입 시점 포트폴리오 전액 투자
        portfolio = round(portfolio * (1 + pnl))
        last_trade_date = curr_date
        trades.append({
            "date": curr["candle_date_time_kst"][:16],
            "buy_datetime": curr["candle_date_time_kst"],
            "sell_datetime": curr["candle_date_time_kst"][:10] + " 23:50:00",
            "buy_price": target,
            "sell_price": raw_sell,
            "pnl": round(pnl, 6),
            "win": pnl > 0,
            "entry_amount": entry_amount,
            "fee": round(entry_amount * FEE_RATE * 2),
        })

    # 현재 신호 계산
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
            "sl_price": round(target * (1 + tb_sl)),
            "trail_pct": tb_trail * 100,
        }

    return build_result(
        "TRAILING_BREAKOUT", trades, initial_capital, current_signal,
        candles=data, k=k, tb_sl=tb_sl, tb_trail=tb_trail,
        tb_ma1_filter=tb_ma1_filter, tb_ma1_period=tb_ma1_period,
        tb_ma2_filter=tb_ma2_filter, tb_ma2_period=tb_ma2_period,
        tb_volume_filter=tb_volume_filter, tb_volume_mult=tb_volume_mult,
        total_candles=len(data),
    )
