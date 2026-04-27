FEE_RATE = 0.0005  # 매수/매도 각 0.05% 수수료


def find_price_lows(closes, window=3):
    """
    가격 기준 로컬 저점 인덱스 반환.
    양쪽 window개보다 낮거나 같은 지점. 배열 끝부분은 오른쪽 비교 대상이
    부족하므로 자동으로 제외된다.
    """
    lows = []
    n = len(closes)
    for i in range(window, n - window):
        if all(closes[i] <= closes[i - j] for j in range(1, window + 1)) and \
           all(closes[i] <= closes[i + j] for j in range(1, window + 1)):
            lows.append(i)
    return lows


def detect_bullish_divergence(closes, rsi_values, lookback=30, window=3, rsi_warmup=15):
    """
    상승 다이버전스 탐지.
    전체 배열에서 가격 로컬 저점을 찾고, 가장 최근 저점(curr)이 lookback 범위 안에
    있으면 그 이전 저점(prev)과 비교한다. prev는 lookback 밖이어도 허용.
    rsi_warmup 이전 인덱스의 저점은 RSI가 신뢰할 수 없으므로 제외.
    - 가격: curr 저점이 prev 저점보다 낮음 (신저점)
    - RSI:  curr 저점 위치의 RSI가 prev 저점 위치보다 높음 (강도 회복)
    반환: (탐지 여부, 이전 저점 RSI, 현재 저점 RSI)
    """
    n = len(closes)
    if n < window * 2 + 2 or len(rsi_values) != n:
        return False, None, None

    # RSI 워밍업 이후 구간에서만 저점 탐색
    all_lows = [i for i in find_price_lows(closes, window) if i >= rsi_warmup]
    if len(all_lows) < 2:
        return False, None, None

    # 가장 최근 저점(curr)이 lookback 범위 안에 있어야 의미 있는 신호
    curr_abs = all_lows[-1]
    if curr_abs < n - lookback:
        return False, None, None

    prev_abs = all_lows[-2]

    price_divergence = closes[curr_abs] < closes[prev_abs]          # 가격 신저점
    rsi_divergence   = rsi_values[curr_abs] > rsi_values[prev_abs]  # RSI 상승

    if price_divergence and rsi_divergence:
        return True, rsi_values[prev_abs], rsi_values[curr_abs]
    return False, None, None


def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi(closes, period=14):
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


def _calc_rsi_series(candles, period):
    """전체 캔들에 대해 RSI 시계열 계산. 워밍업 구간은 None. O(n) 단일 패스."""
    closes = [c["trade_price"] for c in candles]
    return calc_rsi_series_from_closes(closes, period)


def calc_rsi_series_from_closes(closes, period):
    """
    종가 리스트로 RSI 시계열 계산. O(n) 단일 패스 (Wilder EMA).
    워밍업 구간(인덱스 0 ~ period)은 None, 이후는 float.
    """
    n = len(closes)
    result = [None] * n
    if n < period + 1:
        return result

    diffs = [closes[i] - closes[i - 1] for i in range(1, n)]
    gains = [max(d, 0) for d in diffs]
    losses = [abs(min(d, 0)) for d in diffs]

    # Wilder EMA 시드: 첫 period개 SMA
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _rsi_val(ag, al):
        if al == 0:
            return 100.0 if ag > 0 else 50.0
        return 100 - (100 / (1 + ag / al))

    result[period] = round(_rsi_val(avg_gain, avg_loss), 2)

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        result[i + 1] = round(_rsi_val(avg_gain, avg_loss), 2)

    return result


def _find_divergence_points(candles, rsi_series, lookback=30, window=3):
    """
    백테스팅 전 구간에서 다이버전스가 탐지된 캔들 인덱스 목록을 반환.
    슬라이싱 없이 전체 저점 목록을 한 번만 계산한 뒤 인덱스별로 직접 탐색. O(n).
    """
    closes = [c["trade_price"] for c in candles]
    rsi_vals = [v if v is not None else -1.0 for v in rsi_series]
    n = len(closes)
    rsi_warmup = 15

    # 전체 가격 저점 목록을 한 번만 계산
    all_lows = [i for i in find_price_lows(closes, window) if i >= rsi_warmup]

    points = []
    # 저점 목록을 순서대로 순회하며 각 봉 i에서 다이버전스 여부 판단
    for low_idx in range(1, len(all_lows)):
        curr_abs = all_lows[low_idx]
        prev_abs = all_lows[low_idx - 1]

        # curr 저점이 lookback 범위 안에 있어야 의미 있는 신호
        # curr_abs 시점 기준: curr_abs >= n - lookback 이 아닌,
        # 각 봉 i = curr_abs 에서 슬라이스 크기는 curr_abs + 1
        # 즉 슬라이스 크기 내에서 curr_abs가 마지막 lookback 봉 안에 있으면 됨 → 항상 True (마지막 저점)
        # 대신 이전 저점과의 관계만 확인
        price_div = closes[curr_abs] < closes[prev_abs]
        rsi_div   = rsi_vals[curr_abs] > rsi_vals[prev_abs]

        if price_div and rsi_div:
            i = curr_abs
            if points and i - points[-1] < 3:
                points[-1] = i
            else:
                points.append(i)

    return points


def build_result(strategy, trades, initial_capital, current_signal, candles=None, open_trade=None, **extra):
    candle_data = []
    if candles:
        candle_data = [
            {"t": c["candle_date_time_kst"], "o": c["opening_price"],
             "h": c["high_price"], "l": c["low_price"], "c": c["trade_price"],
             "v": c.get("candle_acc_trade_volume", 0)}
            for c in candles
        ]

    # 활성화된 MA 필터별 라인 데이터 계산
    ma_lines = []
    if candles:
        closes = [c["trade_price"] for c in candles]

        # 전략별 MA 필터 키 매핑 (필터 활성화 키, 기간 키)
        ma_filter_keys = [
            ("k_ma1_filter", "k_ma1_period"),    # K변동성돌파 MA1
            ("k_ma2_filter", "k_ma2_period"),    # K변동성돌파 MA2
            ("k_ma3_filter", "k_ma3_period"),    # K변동성돌파 MA3
            ("tb_ma1_filter", "tb_ma1_period"),  # 트레일링돌파 MA1
            ("tb_ma2_filter", "tb_ma2_period"),  # 트레일링돌파 MA2
            ("rsi_ma_filter", "rsi_ma_period"),  # RSI과매도 MA
            ("rdi_ma_filter", "rdi_ma_period"),  # RSI다이버전스 MA
        ]
        seen_periods = set()  # 동일 기간 MA 중복 계산 방지
        for key_f, key_p in ma_filter_keys:
            if extra.get(key_f):
                period = extra.get(key_p)
                if period and period not in seen_periods:
                    seen_periods.add(period)
                    ma_values = [
                        round(sum(closes[i - period + 1:i + 1]) / period) if i >= period - 1 else None
                        for i in range(len(closes))
                    ]
                    ma_lines.append({"period": period, "data": ma_values})

    # RSI 시계열 및 다이버전스 저점 계산 (RSI 관련 전략에서만)
    rsi_line = []
    divergence_points = []
    rsi_period_for_line = None
    if candles:
        if strategy == "RSI_DIVERGENCE_TRAIL":
            rsi_period_for_line = extra.get("rdi_rsi_period", 14)
            lookback = extra.get("rdi_lookback", 30)
        elif strategy == "RSI_OVERSOLD_BOUNCE":
            rsi_period_for_line = extra.get("rsi_period", 14)

        if rsi_period_for_line:
            rsi_line = _calc_rsi_series(candles, rsi_period_for_line)
            # RSI_DIVERGENCE_TRAIL 전략에서는 다이버전스 저점도 표시
            if strategy == "RSI_DIVERGENCE_TRAIL":
                divergence_points = _find_divergence_points(candles, rsi_line, lookback=lookback)

    base = {
        "strategy": strategy,
        "total_trades": 0,
        "win_rate": 0,
        "avg_pnl_per_trade": 0,
        "total_return": 0,
        "initial_capital": initial_capital,
        "final_value": initial_capital,
        "profit_loss": 0,
        "equity_curve": [],
        "current_signal": current_signal,
        "trades": [],
        "candles": candle_data,
        "ma_lines": ma_lines,
        "rsi_line": rsi_line,
        "divergence_points": divergence_points,
        "rsi_period": rsi_period_for_line,
    }
    base.update(extra)

    if not trades and open_trade is None:
        return base

    if not trades:
        if open_trade is not None:
            base["trades"] = [open_trade]
            if open_trade.get("buy_datetime"):
                base["trade_markers"] = [{
                    "buy_datetime": open_trade["buy_datetime"],
                    "sell_datetime": None,
                    "win": None,
                }]
        return base

    wins = sum(1 for t in trades if t["win"])
    win_rate = wins / len(trades)
    avg_pnl = sum(t["pnl"] for t in trades) / len(trades)

    portfolio = initial_capital
    equity_curve = [{"date": "시작", "value": initial_capital}]
    for t in trades:
        prev = portfolio
        portfolio = round(portfolio * (1 + t["pnl"]))
        equity_curve.append({"date": t["date"], "value": portfolio})
        t["krw_pnl"] = portfolio - prev

    total_return = portfolio / initial_capital - 1

    trade_markers = [
        {"buy_datetime": t["buy_datetime"], "sell_datetime": t["sell_datetime"], "win": t["win"]}
        for t in trades
        if "buy_datetime" in t and t.get("sell_datetime")
    ]
    # 보유중인 open trade의 진입 마커도 포함
    if open_trade is not None and open_trade.get("buy_datetime"):
        trade_markers.append({
            "buy_datetime": open_trade["buy_datetime"],
            "sell_datetime": None,
            "win": None,
        })

    displayed = trades[-50:]
    if open_trade is not None:
        displayed = displayed + [open_trade]

    base.update({
        "total_trades": len(trades),
        "win_rate": round(win_rate, 4),
        "avg_pnl_per_trade": round(avg_pnl, 6),
        "total_return": round(total_return, 4),
        "final_value": portfolio,
        "profit_loss": portfolio - initial_capital,
        "equity_curve": equity_curve,
        "trades": displayed,
        "trade_markers": trade_markers,
    })
    return base
