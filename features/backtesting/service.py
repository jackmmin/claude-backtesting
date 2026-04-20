import statistics
from exchanges import get_exchange

MIN_CANDLES = 30
FEE_RATE = 0.0005      # 매수/매도 각 0.05% 수수료
TAKE_PROFIT = 0.05     # 수익률 5% 도달 시 익절 청산


def run_backtest(
    exchange="upbit", market="KRW-BTC",
    strategy="K_VOLATILITY_BREAKOUT",
    k=0.5,
    k_tp=0.05, k_sl=-0.03,
    k_ma_filter=False, k_ma_period=20,
    k_volume_filter=False, k_volume_mult=1.5,
    rsi_period=14, rsi_threshold=30, rsi_exit=62, rsi_tp=0.07, rsi_sl=-0.04,
    rsi_entry_mode="crossover",
    rsi_ma_filter=False, rsi_ma_period=20,
    rsi_volume_filter=False, rsi_volume_mult=1.0,
    rsi_use_tp=True, rsi_use_sl=True, rsi_use_rsi_exit=True,
    rsi_max_hold_bars=0,
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
        return _k_volatility_backtest(data, k=k, initial_capital=initial_capital,
                                      k_tp=k_tp, k_sl=k_sl,
                                      k_ma_filter=k_ma_filter, k_ma_period=k_ma_period,
                                      k_volume_filter=k_volume_filter, k_volume_mult=k_volume_mult)
    if strategy == "RSI_OVERSOLD_BOUNCE":
        return _rsi_oversold_backtest(data, period=rsi_period, threshold=rsi_threshold,
                                      exit_threshold=rsi_exit, take_profit=rsi_tp,
                                      stop_loss=rsi_sl, initial_capital=initial_capital,
                                      entry_mode=rsi_entry_mode,
                                      rsi_ma_filter=rsi_ma_filter, rsi_ma_period=rsi_ma_period,
                                      rsi_volume_filter=rsi_volume_filter, rsi_volume_mult=rsi_volume_mult,
                                      use_tp=rsi_use_tp, use_sl=rsi_use_sl, use_rsi_exit=rsi_use_rsi_exit,
                                      max_hold_bars=rsi_max_hold_bars)
    if strategy == "MA_GOLDEN_CROSS":
        return _ma_golden_cross_backtest(data, fast=ma_fast, slow=ma_slow, initial_capital=initial_capital)
    if strategy == "BOLLINGER_BOUNCE":
        return _bollinger_bounce_backtest(data, period=bb_period, std_mult=bb_std, initial_capital=initial_capital)
    return {"error": f"알 수 없는 전략: {strategy}"}


# ── K변동성 돌파 ──────────────────────────────────────────────────────────────

def _k_volatility_backtest(data, k=0.5, initial_capital=1000000,
                            k_tp=0.05, k_sl=-0.03,
                            k_ma_filter=False, k_ma_period=20,
                            k_volume_filter=False, k_volume_mult=1.5):
    trades = []
    for i in range(1, len(data)):
        prev = data[i - 1]
        curr = data[i]

        # MA 추세 필터: 시가가 MA 아래면 진입 제외
        if k_ma_filter:
            if i < k_ma_period:
                continue
            ma = _sma([c["trade_price"] for c in data[:i]], k_ma_period)
            if ma is not None and curr["opening_price"] < ma:
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

            if curr["high_price"] >= tp_price:
                raw_sell = tp_price
            elif curr["low_price"] <= sl_price:
                raw_sell = sl_price
            else:
                raw_sell = curr["trade_price"]

            sell = raw_sell * (1 - FEE_RATE)
            pnl = (sell - buy_cost) / buy_cost
            trades.append({
                "date": curr["candle_date_time_kst"][:16],
                "buy_datetime": curr["candle_date_time_kst"],
                "sell_datetime": curr["candle_date_time_kst"][:10] + " 23:50:00",
                "buy_price": round(target),
                "sell_price": round(raw_sell),
                "pnl": round(pnl, 6),
                "win": pnl > 0,
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

    return _build_result("K_VOLATILITY_BREAKOUT", trades, initial_capital, current_signal,
                         candles=data, k=k, k_tp=k_tp, k_sl=k_sl,
                         k_ma_filter=k_ma_filter, k_ma_period=k_ma_period,
                         k_volume_filter=k_volume_filter, k_volume_mult=k_volume_mult,
                         total_candles=len(data))


# ── RSI 과매도 반등 ────────────────────────────────────────────────────────────

def _rsi_oversold_backtest(data, period=14, threshold=30, exit_threshold=62,
                            take_profit=0.07, stop_loss=-0.04, initial_capital=1000000,
                            entry_mode="crossover",
                            rsi_ma_filter=False, rsi_ma_period=20,
                            rsi_volume_filter=False, rsi_volume_mult=1.0,
                            use_tp=True, use_sl=True, use_rsi_exit=True,
                            max_hold_bars=0):
    trades = []
    in_trade = False
    entry_price = None
    entry_date = None
    entry_datetime = None
    hold_bars = 0

    for i in range(period + 1, len(data)):
        closes_curr = [c["trade_price"] for c in data[:i + 1]]
        closes_prev = closes_curr[:-1]

        rsi_curr = _rsi(closes_curr, period)
        rsi_prev = _rsi(closes_prev, period)

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
                    ma = _sma(closes_curr, rsi_ma_period)
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
                trades.append({
                    "date": entry_date,
                    "buy_datetime": entry_datetime,
                    "sell_datetime": exited_dt,
                    "buy_price": round(raw_entry),
                    "sell_price": round(exited_sell),
                    "pnl": round(pnl, 6),
                    "win": pnl > 0,
                })
                in_trade = False

    closes = [c["trade_price"] for c in data]
    rsi_curr = _rsi(closes, period)
    rsi_prev = _rsi(closes[:-1], period)
    if entry_mode == "crossover":
        sig_triggered = (rsi_curr is not None and rsi_prev is not None
                         and rsi_curr >= threshold and rsi_prev < threshold)
    else:
        sig_triggered = (rsi_curr is not None and rsi_prev is not None
                         and rsi_curr < threshold and rsi_prev >= threshold)
    current_signal = {
        "date": data[-1]["candle_date_time_kst"][:10],
        "rsi_value": round(rsi_curr, 2) if rsi_curr is not None else None,
        "threshold": threshold,
        "exit_threshold": exit_threshold,
        "entry_mode": entry_mode,
        "triggered": sig_triggered,
        "in_trade": in_trade,
    }

    return _build_result("RSI_OVERSOLD_BOUNCE", trades, initial_capital, current_signal,
                         candles=data, rsi_period=period, rsi_threshold=threshold,
                         rsi_exit=exit_threshold, rsi_tp=take_profit, rsi_sl=stop_loss,
                         entry_mode=entry_mode,
                         rsi_ma_filter=rsi_ma_filter, rsi_ma_period=rsi_ma_period,
                         rsi_volume_filter=rsi_volume_filter, rsi_volume_mult=rsi_volume_mult,
                         use_tp=use_tp, use_sl=use_sl, use_rsi_exit=use_rsi_exit,
                         max_hold_bars=max_hold_bars,
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
