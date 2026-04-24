from .utils import FEE_RATE, sma, detect_bullish_divergence, build_result, calc_rsi_series_from_closes


def _build_rsi_series(data, period):
    """
    전체 캔들에 대해 RSI 시계열을 미리 계산. O(n) 단일 패스.
    워밍업 구간(None)은 -1로 채워 detect_bullish_divergence rsi_warmup 필터가 배제하도록 한다.
    """
    closes = [c["trade_price"] for c in data]
    raw = calc_rsi_series_from_closes(closes, period)
    rsi_series = [r if r is not None else -1.0 for r in raw]
    return closes, rsi_series


def run(data, rsi_period=14, lookback=30, vol_mult=1.5,
        trail_pct=0.03, sl_pct=-0.03,
        ma_filter=False, ma_period=60,
        initial_capital=1000000):
    """
    RSI 상승 다이버전스 + 거래량 급증 + 트레일링 스탑 복합 전략

    [진입 조건]
    1. RSI 상승 다이버전스: 최근 lookback 봉 내 가격 신저점 + RSI는 전 저점 대비 상승
    2. 거래량 급증: 현재 봉 거래량이 최근 20봉 평균의 vol_mult배 이상
    3. (옵션) MA 필터: 현재가가 장기 MA 위에 있을 때만 진입

    [청산 조건]
    - 트레일링 스탑: 진입 후 고점 대비 trail_pct% 하락 시 청산 (수익 극대화)
    - 고정 손절: 진입가 대비 sl_pct% 하락 시 즉시 청산 (손실 제한)
    """
    trades        = []
    portfolio     = initial_capital
    in_trade      = False
    entry_price   = None
    entry_date    = None
    entry_dt      = None
    entry_amount  = None  # 진입 시점 포트폴리오 스냅샷
    peak_price    = None

    # RSI 시계열 전체를 미리 계산 (closes와 인덱스 1:1 대응)
    closes, rsi_series = _build_rsi_series(data, rsi_period)

    # 최소 데이터: rsi 워밍업(period+1) + lookback + window 여유
    min_bars = rsi_period + lookback + 5

    for i in range(min_bars, len(data)):
        curr       = data[i]
        curr_price = curr["trade_price"]

        if in_trade:
            # ── 보유 중: 트레일링 & 손절 관리 ──
            high = curr["high_price"]
            low  = curr["low_price"]

            if high > peak_price:
                peak_price = high

            sl_price    = entry_price * (1 + sl_pct)
            trail_price = peak_price  * (1 - trail_pct)

            raw_sell = None
            if low <= sl_price:
                # 손절 우선
                raw_sell = sl_price
            elif low <= trail_price and trail_price > entry_price:
                # 트레일링 스탑 (수익 구간에서만)
                raw_sell = trail_price

            if raw_sell is not None:
                buy_cost  = entry_price * (1 + FEE_RATE)
                sell_recv = raw_sell    * (1 - FEE_RATE)
                pnl = (sell_recv - buy_cost) / buy_cost
                portfolio = round(portfolio * (1 + pnl))
                trades.append({
                    "date":          entry_date,
                    "buy_datetime":  entry_dt,
                    "sell_datetime": curr["candle_date_time_kst"],
                    "buy_price":     entry_price,
                    "sell_price":    raw_sell,
                    "pnl":           round(pnl, 6),
                    "win":           pnl > 0,
                    "entry_amount":  entry_amount,
                    "fee":           round(entry_amount * FEE_RATE * 2),
                })
                in_trade = False

        else:
            # ── 진입 탐색 ──

            # RSI 다이버전스 탐지 (i+1까지의 슬라이스로 탐지)
            diverged, rsi_prev, rsi_curr_val = detect_bullish_divergence(
                closes[:i + 1], rsi_series[:i + 1], lookback=lookback
            )
            if not diverged:
                continue

            # 거래량 급증 필터
            vol_window = data[max(0, i - 20):i]
            vols       = [c.get("candle_acc_trade_volume", 0) for c in vol_window]
            avg_vol    = sum(vols) / len(vol_window) if vol_window else 0
            curr_vol   = curr.get("candle_acc_trade_volume", 0)
            if avg_vol > 0 and curr_vol < avg_vol * vol_mult:
                continue

            # MA 추세 필터 (옵션)
            if ma_filter:
                ma_val = sma(closes[:i + 1], ma_period)
                if ma_val is not None and curr_price < ma_val:
                    continue

            # 다음 봉 시가로 진입
            if i + 1 >= len(data):
                continue
            next_open    = data[i + 1]["opening_price"]
            entry_price  = next_open
            entry_date   = curr["candle_date_time_kst"][:10]
            entry_dt     = data[i + 1]["candle_date_time_kst"]
            entry_amount = portfolio
            peak_price   = next_open
            in_trade     = True

    # 미청산 포지션: 현재가 기준 미실현 손익
    open_trade = None
    if in_trade and entry_price is not None:
        last       = data[-1]
        curr_price = last["trade_price"]
        if last["high_price"] > peak_price:
            peak_price = last["high_price"]
        buy_cost    = entry_price * (1 + FEE_RATE)
        sell_recv   = curr_price  * (1 - FEE_RATE)
        pnl_unreal  = (sell_recv - buy_cost) / buy_cost
        open_trade  = {
            "date":          entry_date,
            "buy_datetime":  entry_dt,
            "sell_datetime": "",
            "buy_price":     entry_price,
            "sell_price":    curr_price,
            "pnl":           round(pnl_unreal, 6),
            "win":           pnl_unreal > 0,
            "open":          True,
        }

    # 현재 신호 상태 (마지막 봉 기준)
    diverged_now, _, _ = detect_bullish_divergence(closes, rsi_series, lookback=lookback)
    vol_window_now = data[max(0, len(data) - 21):len(data) - 1]
    vols_now       = [c.get("candle_acc_trade_volume", 0) for c in vol_window_now]
    avg_vol_now    = sum(vols_now) / len(vols_now) if vols_now else 0
    last_vol       = data[-1].get("candle_acc_trade_volume", 0)
    vol_ok         = avg_vol_now > 0 and last_vol >= avg_vol_now * vol_mult

    current_signal = {
        "date":       data[-1]["candle_date_time_kst"][:16],
        "rsi_value":  round(rsi_series[-1], 2),
        "divergence": diverged_now,
        "vol_ratio":  round(last_vol / avg_vol_now, 2) if avg_vol_now > 0 else 0,
        "vol_ok":     vol_ok,
        "triggered":  diverged_now and vol_ok,
        "in_trade":   in_trade,
        "trail_pct":  trail_pct * 100,
        "sl_pct":     abs(sl_pct) * 100,
    }

    return build_result(
        "RSI_DIVERGENCE_TRAIL", trades, initial_capital, current_signal,
        open_trade=open_trade,
        candles=data,
        rdi_rsi_period=rsi_period,
        rdi_lookback=lookback,
        rdi_vol_mult=vol_mult,
        rdi_trail_pct=trail_pct,
        rdi_sl_pct=sl_pct,
        rdi_ma_filter=ma_filter,
        rdi_ma_period=ma_period,
        total_candles=len(data),
    )
