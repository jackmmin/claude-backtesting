import statistics
from exchanges import get_exchange

MIN_CANDLES = 30


def calculate_signals(exchange="upbit", market="KRW-BTC", count=200, interval="days"):
    exch = get_exchange(exchange)
    candles = exch.get_candles_bulk(market, count=count, interval=interval)

    if len(candles) < MIN_CANDLES:
        return {"error": f"데이터 부족: {len(candles)}개 (최소 {MIN_CANDLES}개 필요)"}

    data = list(reversed(candles))
    is_minute = interval.startswith("minutes")

    signals = [
        _calc_k_volatility_signal(data),
        _calc_rsi_signal(data, is_minute=is_minute),
        _calc_ma_golden_cross_signal(data),
        _calc_bollinger_bounce_signal(data),
    ]

    historical_signals = _find_historical_signals(data, is_minute=is_minute)

    return {
        "market": market,
        "interval": interval,
        "signals": signals,
        "historical_signals": historical_signals,
    }


def _calc_k_volatility_signal(data, k=0.5):
    prev = data[-2]
    curr = data[-1]
    prev_range = prev["high_price"] - prev["low_price"]
    target = curr["opening_price"] + k * prev_range
    triggered = curr["high_price"] >= target

    return {
        "strategy": "K_VOLATILITY_BREAKOUT",
        "name": "K변동성돌파",
        "triggered": triggered,
        "description": f"목표가 {'돌파 중' if triggered else '미달'} ({_fmt(round(target))})",
        "details": {
            "target_price": round(target),
            "current_price": curr["trade_price"],
            "open_price": curr["opening_price"],
            "prev_range": round(prev_range),
            "k": k,
        },
    }


def _calc_rsi_signal(data, period=14, threshold=30, is_minute=False):
    closes = [c["trade_price"] for c in data]
    rsi_curr = _rsi(closes, period)
    rsi_prev = _rsi(closes[:-1], period)

    if rsi_curr is None:
        return {
            "strategy": "RSI_OVERSOLD_BOUNCE",
            "name": "RSI 과매도 반등",
            "triggered": False,
            "description": "데이터 부족",
            "details": {"rsi_value": None, "threshold": threshold, "period": period},
        }

    # 진입 신호: RSI가 과매도에서 threshold 위로 회복
    triggered = rsi_prev is not None and rsi_curr >= threshold and rsi_prev < threshold
    desc = f"RSI {rsi_curr:.1f} ({'반등 진입' if triggered else '과매도' if rsi_curr < threshold else '정상 범위'})"

    period_label = "봉" if is_minute else "일봉"
    return {
        "strategy": "RSI_OVERSOLD_BOUNCE",
        "name": "RSI 과매도 반등",
        "triggered": triggered,
        "description": desc,
        "details": {"rsi_value": round(rsi_curr, 2), "threshold": threshold, "period": period, "period_label": period_label},
    }


def _calc_ma_golden_cross_signal(data):
    closes = [c["trade_price"] for c in data]
    ma5 = _sma(closes, 5)
    ma20 = _sma(closes, 20)

    if ma5 is None or ma20 is None:
        return {
            "strategy": "MA_GOLDEN_CROSS",
            "name": "골든크로스",
            "triggered": False,
            "description": "데이터 부족",
            "details": {"ma5": None, "ma20": None, "cross_candles_ago": None},
        }

    cross_candles_ago = None
    for i in range(1, min(4, len(closes))):
        idx = len(closes) - i
        if idx < 20:
            break
        ma5_before = _sma(closes[:idx], 5)
        ma20_before = _sma(closes[:idx], 20)
        ma5_after = _sma(closes[:idx + 1], 5)
        ma20_after = _sma(closes[:idx + 1], 20)
        if (ma5_before is not None and ma20_before is not None and
                ma5_before <= ma20_before and ma5_after > ma20_after):
            cross_candles_ago = i - 1
            break

    triggered = ma5 > ma20 and cross_candles_ago is not None
    desc = f"MA5({_fmt(round(ma5))}) {'>' if ma5 > ma20 else '<'} MA20({_fmt(round(ma20))})"

    return {
        "strategy": "MA_GOLDEN_CROSS",
        "name": "골든크로스",
        "triggered": triggered,
        "description": desc,
        "details": {
            "ma5": round(ma5),
            "ma20": round(ma20),
            "cross_candles_ago": cross_candles_ago,
        },
    }


def _calc_bollinger_bounce_signal(data, period=20, std_mult=2.0):
    closes = [c["trade_price"] for c in data]
    if len(closes) < period + 1:
        return {
            "strategy": "BOLLINGER_BOUNCE",
            "name": "볼린저밴드 반등",
            "triggered": False,
            "description": "데이터 부족",
            "details": {"lower_band": None, "middle_band": None, "upper_band": None, "current_price": None},
        }

    last = closes[-period:]
    middle = sum(last) / period
    std = statistics.stdev(last)
    lower = middle - std_mult * std
    upper = middle + std_mult * std

    prev_close = closes[-2]
    curr_close = closes[-1]
    triggered = prev_close < lower and curr_close >= lower

    desc = f"현재가 {'하단밴드 반등' if triggered else '하단밴드 근접' if curr_close < lower * 1.01 else '정상 범위'}"

    return {
        "strategy": "BOLLINGER_BOUNCE",
        "name": "볼린저밴드 반등",
        "triggered": triggered,
        "description": desc,
        "details": {
            "lower_band": round(lower),
            "middle_band": round(middle),
            "upper_band": round(upper),
            "current_price": curr_close,
        },
    }


def _find_historical_signals(data, k=0.5, is_minute=False):
    signal_map = {}

    for i in range(1, len(data) - 1):
        window = data[:i + 1]
        triggered_strategies = []

        # K변동성돌파
        prev = data[i - 1]
        curr = data[i]
        prev_range = prev["high_price"] - prev["low_price"]
        if prev_range > 0:
            target = curr["opening_price"] + k * prev_range
            if curr["high_price"] >= target:
                triggered_strategies.append("K_VOLATILITY_BREAKOUT")

        # RSI: 과매도 회복 크로스 (threshold 위로 재진입)
        closes = [c["trade_price"] for c in window]
        rsi_curr = _rsi(closes, 14)
        rsi_prev = _rsi(closes[:-1], 14)
        if (rsi_curr is not None and rsi_prev is not None
                and rsi_curr >= 30 and rsi_prev < 30):
            triggered_strategies.append("RSI_OVERSOLD_BOUNCE")

        # MA 골든크로스
        if len(closes) >= 21:
            ma5_curr = _sma(closes, 5)
            ma20_curr = _sma(closes, 20)
            ma5_prev = _sma(closes[:-1], 5)
            ma20_prev = _sma(closes[:-1], 20)
            if (ma5_prev is not None and ma20_prev is not None and
                    ma5_prev <= ma20_prev and ma5_curr > ma20_curr):
                triggered_strategies.append("MA_GOLDEN_CROSS")

        # 볼린저밴드 반등
        if len(closes) >= 21:
            last = closes[-20:]
            middle = sum(last) / 20
            std = statistics.stdev(last)
            lower = middle - 2.0 * std
            if len(closes) >= 2 and closes[-2] < lower and closes[-1] >= lower:
                triggered_strategies.append("BOLLINGER_BOUNCE")

        if triggered_strategies:
            kst = curr["candle_date_time_kst"]
            # 분봉: 전체 datetime을 키로 사용(봉 단위 정밀도), 일봉 이상: 날짜만
            key = kst if is_minute else kst[:10]
            signal_map[key] = triggered_strategies

    items = sorted(signal_map.items(), reverse=True)
    if is_minute:
        return [{"datetime": dt, "date": dt[:10], "strategies": s} for dt, s in items]
    return [{"datetime": None, "date": d, "strategies": s} for d, s in items]


def _sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    diffs = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in diffs]
    losses = [abs(min(d, 0)) for d in diffs]
    # Wilder EMA: SMA 시드 후 지수 스무딩
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100 - (100 / (1 + avg_gain / avg_loss))


def _fmt(n):
    return f"{n:,}"
