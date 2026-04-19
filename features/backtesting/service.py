import statistics
from exchanges import get_exchange

MIN_CANDLES = 30
FEE_RATE = 0.0005      # 매수/매도 각 0.05% 수수료
TAKE_PROFIT = 0.05     # 수익률 5% 도달 시 익절 청산


def run_backtest(
    exchange="upbit", market="KRW-BTC",
    strategy="K_VOLATILITY_BREAKOUT",
    k=0.5,
    rsi_period=14, rsi_threshold=30, rsi_exit=50,
    ma_fast=5, ma_slow=20,
    bb_period=20, bb_std=2.0,
    interval="days", count=200, initial_capital=1000000,
):
    exch = get_exchange(exchange)
    candles = exch.get_candles_bulk(market, count=count, interval=interval)

    if len(candles) < MIN_CANDLES:
        return {"error": f"데이터 부족: {len(candles)}개 수집 (최소 {MIN_CANDLES}개 필요)"}

    data = list(reversed(candles))

    if strategy == "K_VOLATILITY_BREAKOUT":
        return _k_volatility_backtest(data, k=k, initial_capital=initial_capital)
    if strategy == "RSI_OVERSOLD_BOUNCE":
        return _rsi_oversold_backtest(data, period=rsi_period, threshold=rsi_threshold,
                                      exit_threshold=rsi_exit, initial_capital=initial_capital)
    if strategy == "MA_GOLDEN_CROSS":
        return _ma_golden_cross_backtest(data, fast=ma_fast, slow=ma_slow, initial_capital=initial_capital)
    if strategy == "BOLLINGER_BOUNCE":
        return _bollinger_bounce_backtest(data, period=bb_period, std_mult=bb_std, initial_capital=initial_capital)
    return {"error": f"알 수 없는 전략: {strategy}"}


# ── K변동성 돌파 ──────────────────────────────────────────────────────────────

def _k_volatility_backtest(data, k=0.5, initial_capital=1000000):
    trades = []
    for i in range(1, len(data)):
        prev = data[i - 1]
        curr = data[i]

        prev_range = prev["trade_price"] - prev["low_price"]
        if prev_range <= 0:
            continue

        target = curr["opening_price"] + k * prev_range
        # 당일 고가가 목표가 이상일 때 진입 (고가 기준으로 look-ahead bias 방지)
        if curr["high_price"] >= target:
            buy_cost = target * (1 + FEE_RATE)   # 매수 수수료 반영
            tp_price = target * (1 + TAKE_PROFIT)
            # 당일 고가가 TP 가격 이상이면 TP 청산, 아니면 당일 종가 청산
            if curr["high_price"] >= tp_price:
                raw_sell = tp_price
            else:
                raw_sell = curr["trade_price"]
            sell = raw_sell * (1 - FEE_RATE)  # 매도 수수료 반영
            pnl = (sell - buy_cost) / buy_cost
            trades.append({
                "date": curr["candle_date_time_kst"][:16],
                "buy_datetime": curr["candle_date_time_kst"],
                "sell_datetime": curr["candle_date_time_kst"][:10] + " 23:50:00",
                "buy_price": round(target),   # 표시용: 수수료 전 목표가
                "sell_price": round(raw_sell),  # 표시용: 수수료 전 종가
                "pnl": round(pnl, 6),
                "win": pnl > 0,
            })

    current_signal = None
    if len(data) >= 2:
        prev = data[-2]
        curr = data[-1]
        prev_range = prev["trade_price"] - prev["low_price"]
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

    return _build_result("K_VOLATILITY_BREAKOUT", trades, initial_capital, current_signal,
                         candles=data, k=k, total_candles=len(data))


# ── RSI 과매도 반등 ────────────────────────────────────────────────────────────

def _rsi_oversold_backtest(data, period=14, threshold=30, exit_threshold=50, initial_capital=1000000):
    trades = []
    in_trade = False
    entry_price = None
    entry_date = None
    entry_datetime = None

    for i in range(period + 1, len(data)):
        closes_curr = [c["trade_price"] for c in data[:i + 1]]
        closes_prev = closes_curr[:-1]

        rsi_curr = _rsi(closes_curr, period)
        rsi_prev = _rsi(closes_prev, period)

        if rsi_curr is None:
            continue

        if not in_trade:
            if rsi_curr < threshold and (rsi_prev is None or rsi_prev >= threshold):
                if i + 1 < len(data):
                    entry_price = data[i + 1]["opening_price"] * (1 + FEE_RATE)  # 매수 수수료 반영
                    entry_date = data[i]["candle_date_time_kst"][:10]
                    entry_datetime = data[i + 1]["candle_date_time_kst"]  # 실제 체결 봉 datetime
                    in_trade = True
        else:
            tp_price = (entry_price / (1 + FEE_RATE)) * (1 + TAKE_PROFIT)
            if data[i]["high_price"] >= tp_price:
                # TP 도달: 해당 봉 고가 기준 익절 청산
                raw_sell = tp_price
                sell_price = raw_sell * (1 - FEE_RATE)
                pnl = (sell_price - entry_price) / entry_price
                trades.append({
                    "date": entry_date,
                    "buy_datetime": entry_datetime,
                    "sell_datetime": data[i]["candle_date_time_kst"],
                    "buy_price": round(entry_price / (1 + FEE_RATE)),
                    "sell_price": round(raw_sell),
                    "pnl": round(pnl, 6),
                    "win": pnl > 0,
                })
                in_trade = False
            elif rsi_curr >= exit_threshold:
                if i + 1 < len(data):
                    raw_sell = data[i + 1]["opening_price"]
                    sell_price = raw_sell * (1 - FEE_RATE)  # 매도 수수료 반영
                    pnl = (sell_price - entry_price) / entry_price
                    trades.append({
                        "date": entry_date,
                        "buy_datetime": entry_datetime,
                        "sell_datetime": data[i]["candle_date_time_kst"],
                        "buy_price": round(entry_price / (1 + FEE_RATE)),  # 표시용: 수수료 전 가격
                        "sell_price": round(raw_sell),  # 표시용: 수수료 전 가격
                        "pnl": round(pnl, 6),
                        "win": pnl > 0,
                    })
                    in_trade = False

    closes = [c["trade_price"] for c in data]
    rsi_curr = _rsi(closes, period)
    rsi_prev = _rsi(closes[:-1], period)
    current_signal = {
        "date": data[-1]["candle_date_time_kst"][:10],
        "rsi_value": round(rsi_curr, 2) if rsi_curr is not None else None,
        "threshold": threshold,
        "exit_threshold": exit_threshold,
        "triggered": rsi_curr is not None and rsi_curr < threshold and (rsi_prev is None or rsi_prev >= threshold),
        "in_trade": in_trade,
    }

    return _build_result("RSI_OVERSOLD_BOUNCE", trades, initial_capital, current_signal,
                         candles=data, rsi_period=period, rsi_threshold=threshold, rsi_exit=exit_threshold,
                         total_candles=len(data))


# ── MA 골든크로스 ──────────────────────────────────────────────────────────────

def _ma_golden_cross_backtest(data, fast=5, slow=20, initial_capital=1000000):
    trades = []
    in_trade = False
    entry_price = None
    entry_date = None
    entry_datetime = None

    for i in range(slow + 1, len(data)):
        closes_curr = [c["trade_price"] for c in data[:i + 1]]
        closes_prev = closes_curr[:-1]

        ma_fast_curr = _sma(closes_curr, fast)
        ma_slow_curr = _sma(closes_curr, slow)
        ma_fast_prev = _sma(closes_prev, fast)
        ma_slow_prev = _sma(closes_prev, slow)

        if None in (ma_fast_curr, ma_slow_curr, ma_fast_prev, ma_slow_prev):
            continue

        if not in_trade:
            if ma_fast_prev <= ma_slow_prev and ma_fast_curr > ma_slow_curr:
                if i + 1 < len(data):
                    entry_price = data[i + 1]["opening_price"] * (1 + FEE_RATE)  # 매수 수수료 반영
                    entry_date = data[i]["candle_date_time_kst"][:10]
                    entry_datetime = data[i + 1]["candle_date_time_kst"]  # 실제 체결 봉 datetime
                    in_trade = True
        else:
            tp_price = (entry_price / (1 + FEE_RATE)) * (1 + TAKE_PROFIT)
            if data[i]["high_price"] >= tp_price:
                # TP 도달: 해당 봉 고가 기준 익절 청산
                raw_sell = tp_price
                sell_price = raw_sell * (1 - FEE_RATE)
                pnl = (sell_price - entry_price) / entry_price
                trades.append({
                    "date": entry_date,
                    "buy_datetime": entry_datetime,
                    "sell_datetime": data[i]["candle_date_time_kst"],
                    "buy_price": round(entry_price / (1 + FEE_RATE)),
                    "sell_price": round(raw_sell),
                    "pnl": round(pnl, 6),
                    "win": pnl > 0,
                })
                in_trade = False
            elif ma_fast_prev >= ma_slow_prev and ma_fast_curr < ma_slow_curr:
                if i + 1 < len(data):
                    raw_sell = data[i + 1]["opening_price"]
                    sell_price = raw_sell * (1 - FEE_RATE)  # 매도 수수료 반영
                    pnl = (sell_price - entry_price) / entry_price
                    trades.append({
                        "date": entry_date,
                        "buy_datetime": entry_datetime,
                        "sell_datetime": data[i]["candle_date_time_kst"],
                        "buy_price": round(entry_price / (1 + FEE_RATE)),  # 표시용: 수수료 전 가격
                        "sell_price": round(raw_sell),  # 표시용: 수수료 전 가격
                        "pnl": round(pnl, 6),
                        "win": pnl > 0,
                    })
                    in_trade = False

    closes = [c["trade_price"] for c in data]
    ma_fast_val = _sma(closes, fast)
    ma_slow_val = _sma(closes, slow)
    ma_fast_prev = _sma(closes[:-1], fast)
    ma_slow_prev = _sma(closes[:-1], slow)
    golden_cross = (
        ma_fast_prev is not None and ma_slow_prev is not None
        and ma_fast_val is not None and ma_slow_val is not None
        and ma_fast_prev <= ma_slow_prev and ma_fast_val > ma_slow_val
    )
    current_signal = {
        "date": data[-1]["candle_date_time_kst"][:10],
        "ma_fast": round(ma_fast_val) if ma_fast_val is not None else None,
        "ma_slow": round(ma_slow_val) if ma_slow_val is not None else None,
        "fast_period": fast,
        "slow_period": slow,
        "triggered": golden_cross,
        "in_trade": in_trade,
    }

    return _build_result("MA_GOLDEN_CROSS", trades, initial_capital, current_signal,
                         candles=data, ma_fast=fast, ma_slow=slow, total_candles=len(data))


# ── 볼린저밴드 반등 ────────────────────────────────────────────────────────────

def _bollinger_bounce_backtest(data, period=20, std_mult=2.0, initial_capital=1000000):
    trades = []
    in_trade = False
    entry_price = None
    entry_date = None
    entry_datetime = None

    for i in range(period + 1, len(data)):
        closes = [c["trade_price"] for c in data[:i + 1]]
        last = closes[-period:]
        if len(last) < 2:
            continue

        middle = sum(last) / period
        std = statistics.stdev(last)
        lower = middle - std_mult * std

        curr_close = closes[-1]
        prev_close = closes[-2]

        if not in_trade:
            if prev_close < lower and curr_close >= lower:
                if i + 1 < len(data):
                    entry_price = data[i + 1]["opening_price"] * (1 + FEE_RATE)  # 매수 수수료 반영
                    entry_date = data[i]["candle_date_time_kst"][:10]
                    entry_datetime = data[i + 1]["candle_date_time_kst"]  # 실제 체결 봉 datetime
                    in_trade = True
        else:
            tp_price = (entry_price / (1 + FEE_RATE)) * (1 + TAKE_PROFIT)
            if data[i]["high_price"] >= tp_price:
                # TP 도달: 해당 봉 고가 기준 익절 청산
                raw_sell = tp_price
                sell_price = raw_sell * (1 - FEE_RATE)
                pnl = (sell_price - entry_price) / entry_price
                trades.append({
                    "date": entry_date,
                    "buy_datetime": entry_datetime,
                    "sell_datetime": data[i]["candle_date_time_kst"],
                    "buy_price": round(entry_price / (1 + FEE_RATE)),
                    "sell_price": round(raw_sell),
                    "pnl": round(pnl, 6),
                    "win": pnl > 0,
                })
                in_trade = False
            elif curr_close >= middle:
                if i + 1 < len(data):
                    raw_sell = data[i + 1]["opening_price"]
                    sell_price = raw_sell * (1 - FEE_RATE)  # 매도 수수료 반영
                    pnl = (sell_price - entry_price) / entry_price
                    trades.append({
                        "date": entry_date,
                        "buy_datetime": entry_datetime,
                        "sell_datetime": data[i]["candle_date_time_kst"],
                        "buy_price": round(entry_price / (1 + FEE_RATE)),  # 표시용: 수수료 전 가격
                        "sell_price": round(raw_sell),  # 표시용: 수수료 전 가격
                        "pnl": round(pnl, 6),
                        "win": pnl > 0,
                    })
                    in_trade = False

    closes = [c["trade_price"] for c in data]
    last = closes[-period:] if len(closes) >= period else closes
    middle = sum(last) / len(last)
    std = statistics.stdev(last) if len(last) >= 2 else 0
    lower = middle - std_mult * std
    upper = middle + std_mult * std
    bounce = len(closes) >= 2 and closes[-2] < lower and closes[-1] >= lower

    current_signal = {
        "date": data[-1]["candle_date_time_kst"][:10],
        "current_price": closes[-1],
        "lower_band": round(lower),
        "middle_band": round(middle),
        "upper_band": round(upper),
        "triggered": bounce,
        "in_trade": in_trade,
    }

    return _build_result("BOLLINGER_BOUNCE", trades, initial_capital, current_signal,
                         candles=data, bb_period=period, bb_std=std_mult, total_candles=len(data))


# ── 공통 결과 빌더 ─────────────────────────────────────────────────────────────

def _build_result(strategy, trades, initial_capital, current_signal, candles=None, **extra):
    candle_data = []
    if candles:
        candle_data = [
            {"t": c["candle_date_time_kst"], "o": c["opening_price"],
             "h": c["high_price"], "l": c["low_price"], "c": c["trade_price"]}
            for c in candles
        ]
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
    }
    base.update(extra)

    if not trades:
        return base

    wins = sum(1 for t in trades if t["win"])
    win_rate = wins / len(trades)
    avg_pnl = sum(t["pnl"] for t in trades) / len(trades)

    portfolio = initial_capital
    equity_curve = []
    for t in trades:
        prev = portfolio
        portfolio = round(portfolio * (1 + t["pnl"]))
        equity_curve.append({"date": t["date"], "value": portfolio})
        t["krw_pnl"] = portfolio - prev

    total_return = portfolio / initial_capital - 1

    trade_markers = [
        {"buy_datetime": t["buy_datetime"], "sell_datetime": t["sell_datetime"], "win": t["win"]}
        for t in trades
        if "buy_datetime" in t and "sell_datetime" in t
    ]
    base.update({
        "total_trades": len(trades),
        "win_rate": round(win_rate, 4),
        "avg_pnl_per_trade": round(avg_pnl, 6),
        "total_return": round(total_return, 4),
        "final_value": portfolio,
        "profit_loss": portfolio - initial_capital,
        "equity_curve": equity_curve,
        "trades": trades[-50:],
        "trade_markers": trade_markers,
    })
    return base


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
