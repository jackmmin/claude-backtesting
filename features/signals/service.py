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
    # RSI 시계열을 O(n) 단일 패스로 계산 후 마지막 두 값만 사용
    rsi_vals = _rsi_series(closes, period)
    rsi_curr = rsi_vals[-1] if len(rsi_vals) >= 1 else None
    rsi_prev = rsi_vals[-2] if len(rsi_vals) >= 2 else None

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
    n = len(closes)
    if n < 20:
        return {
            "strategy": "MA_GOLDEN_CROSS",
            "name": "골든크로스",
            "triggered": False,
            "description": "데이터 부족",
            "details": {"ma5": None, "ma20": None, "cross_candles_ago": None},
        }

    # 슬라이싱 없이 인덱스 직접 참조 — 최근 봉 3개만 확인
    ma5  = sum(closes[n - 5:n])  / 5
    ma20 = sum(closes[n - 20:n]) / 20

    cross_candles_ago = None
    for i in range(1, min(4, n - 19)):
        e = n - i          # 현재 창 끝 (exclusive)
        ma5_c  = sum(closes[e - 5:e])   / 5
        ma20_c = sum(closes[e - 20:e])  / 20
        ma5_p  = sum(closes[e - 6:e - 1]) / 5
        ma20_p = sum(closes[e - 21:e - 1]) / 20
        if ma5_p <= ma20_p and ma5_c > ma20_c:
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
    """
    전체 히스토리 신호 탐색. 모든 지표를 O(n) 단일 패스로 계산.
    - RSI: _rsi_series()로 미리 전체 시계열 계산
    - MA5/MA20: prefix sum으로 O(1) 창 합산
    - 볼린저: sum/sum-of-squares prefix로 O(1) 평균·분산 계산
    """
    closes = [c["trade_price"] for c in data]
    n = len(closes)

    # ── RSI 시계열 한 번만 계산 ──
    rsi_vals = _rsi_series(closes, 14)

    # ── prefix sum (MA5, MA20) ──
    prefix = [0.0] * (n + 1)
    for i, v in enumerate(closes):
        prefix[i + 1] = prefix[i] + v

    def _window_sum(end_excl, length):
        """closes[end_excl-length : end_excl] 합계 O(1)"""
        return prefix[end_excl] - prefix[end_excl - length]

    # ── 볼린저 prefix (sum, sum of squares) ──
    prefix_sq = [0.0] * (n + 1)
    for i, v in enumerate(closes):
        prefix_sq[i + 1] = prefix_sq[i] + v * v

    def _bollinger_params(end_excl, period=20):
        """[end_excl-period, end_excl) 구간의 (mean, lower_band)를 O(1)로 반환.
        기존 statistics.stdev와 동일하게 표본 표준편차(n-1 분모) 사용."""
        s  = prefix[end_excl]    - prefix[end_excl - period]
        s2 = prefix_sq[end_excl] - prefix_sq[end_excl - period]
        mean = s / period
        # 표본 분산: (Σx² - n·mean²) / (n-1)
        var  = (s2 - period * mean * mean) / (period - 1)
        std  = var ** 0.5 if var > 0 else 0.0
        return mean, mean - 2.0 * std

    signal_map = {}

    for i in range(1, n - 1):
        curr = data[i]
        triggered_strategies = []

        # ── K변동성돌파 ──
        prev_range = data[i - 1]["high_price"] - data[i - 1]["low_price"]
        if prev_range > 0:
            target = curr["opening_price"] + k * prev_range
            if curr["high_price"] >= target:
                triggered_strategies.append("K_VOLATILITY_BREAKOUT")

        # ── RSI 과매도 회복 크로스 ──
        rc = rsi_vals[i]
        rp = rsi_vals[i - 1]
        if rc is not None and rp is not None and rc >= 30 and rp < 30:
            triggered_strategies.append("RSI_OVERSOLD_BOUNCE")

        # ── MA 골든크로스 (prefix sum, O(1)) ──
        if i >= 20:
            e = i + 1  # exclusive end (현재 봉 포함)
            ma5_c  = _window_sum(e,     5)  / 5
            ma20_c = _window_sum(e,    20)  / 20
            ma5_p  = _window_sum(e - 1, 5)  / 5
            ma20_p = _window_sum(e - 1, 20) / 20
            if ma5_p <= ma20_p and ma5_c > ma20_c:
                triggered_strategies.append("MA_GOLDEN_CROSS")

        # ── 볼린저밴드 반등 (prefix sum, O(1)) ──
        if i >= 20:
            _, lower = _bollinger_params(i + 1)  # closes[i-19..i] 기준
            if closes[i - 1] < lower and closes[i] >= lower:
                triggered_strategies.append("BOLLINGER_BOUNCE")

        if triggered_strategies:
            kst = curr["candle_date_time_kst"]
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


def _rsi_series(closes, period=14):
    """전체 RSI 시계열을 O(n) 단일 패스로 계산. 워밍업 구간은 None."""
    n = len(closes)
    result = [None] * n
    if n < period + 1:
        return result
    diffs = [closes[i] - closes[i - 1] for i in range(1, n)]
    gains = [max(d, 0) for d in diffs]
    losses = [abs(min(d, 0)) for d in diffs]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _val(ag, al):
        if al == 0:
            return 100.0 if ag > 0 else 50.0
        return 100 - (100 / (1 + ag / al))

    result[period] = _val(avg_gain, avg_loss)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        result[i + 1] = _val(avg_gain, avg_loss)
    return result


def _fmt(n):
    return f"{n:,}"
