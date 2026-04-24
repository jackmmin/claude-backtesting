import statistics

FEE_RATE = 0.0005  # 매수/매도 각 0.05% 수수료


def find_local_lows(values, window=5):
    """
    로컬 저점 인덱스 반환: 양쪽 window개보다 작은 지점
    """
    lows = []
    for i in range(window, len(values) - window):
        if all(values[i] <= values[i - j] for j in range(1, window + 1)) and \
           all(values[i] <= values[i + j] for j in range(1, window + 1)):
            lows.append(i)
    return lows


def detect_bullish_divergence(closes, rsi_values, lookback=30, window=3):
    """
    상승 다이버전스 탐지: 최근 lookback 봉 내에서
    - 가격: 신저점 (이전 저점보다 낮음)
    - RSI: 전 저점보다 높음 (다이버전스)
    반환: (탐지 여부, 이전 저점 RSI, 현재 저점 RSI)
    """
    if len(closes) < lookback + window * 2:
        return False, None, None

    recent_closes = closes[-lookback:]
    recent_rsi    = rsi_values[-lookback:]

    price_lows = find_local_lows(recent_closes, window)
    rsi_lows   = find_local_lows(recent_rsi,   window)

    # 공통 저점 인덱스 교집합 (허용 오차 ±1)
    matched = []
    for pi in price_lows:
        for ri in rsi_lows:
            if abs(pi - ri) <= 1:
                matched.append(pi)
                break

    if len(matched) < 2:
        return False, None, None

    prev_idx = matched[-2]
    curr_idx = matched[-1]

    price_divergence = recent_closes[curr_idx] < recent_closes[prev_idx]
    rsi_divergence   = recent_rsi[curr_idx]    > recent_rsi[prev_idx]

    if price_divergence and rsi_divergence:
        return True, recent_rsi[prev_idx], recent_rsi[curr_idx]
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
        # K변동성돌파: 3개 MA 필터
        for key_f, key_p in [("k_ma1_filter", "k_ma1_period"),
                              ("k_ma2_filter", "k_ma2_period"),
                              ("k_ma3_filter", "k_ma3_period")]:
            if extra.get(key_f):
                period = extra.get(key_p)
                if period:
                    ma_values = [
                        round(sum(closes[i - period + 1:i + 1]) / period) if i >= period - 1 else None
                        for i in range(len(closes))
                    ]
                    ma_lines.append({"period": period, "data": ma_values})
        # RSI 전략: 단일 MA 필터
        if extra.get("rsi_ma_filter"):
            period = extra.get("rsi_ma_period")
            if period:
                ma_values = [
                    round(sum(closes[i - period + 1:i + 1]) / period) if i >= period - 1 else None
                    for i in range(len(closes))
                ]
                ma_lines.append({"period": period, "data": ma_values})

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
    }
    base.update(extra)

    if not trades and open_trade is None:
        return base

    if not trades:
        if open_trade is not None:
            base["trades"] = [open_trade]
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
