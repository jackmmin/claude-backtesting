from exchanges import get_exchange

MIN_CANDLES = 30


def run_backtest(exchange="upbit", market="KRW-BTC", k=0.5, interval="days", count=200, initial_capital=1000000):
    exch = get_exchange(exchange)

    candles = exch.get_candles_bulk(market, count=count, interval=interval)

    if len(candles) < MIN_CANDLES:
        return {
            "error": f"데이터 부족: {len(candles)}개 수집 (최소 {MIN_CANDLES}개 필요)"
        }

    return _k_volatility_backtest(candles, k=k, initial_capital=initial_capital)


def _k_volatility_backtest(candles, k=0.5, initial_capital=1000000):
    # Upbit returns newest-first; reverse to chronological order
    data = list(reversed(candles))

    trades = []
    for i in range(1, len(data) - 1):
        prev = data[i - 1]
        curr = data[i]
        next_day = data[i + 1]

        prev_range = prev["high_price"] - prev["low_price"]
        if prev_range <= 0:
            continue

        target = curr["opening_price"] + k * prev_range

        if curr["high_price"] >= target:
            sell = next_day["opening_price"]
            pnl = (sell - target) / target
            trades.append({
                "date": curr["candle_date_time_kst"][:10],
                "buy_price": round(target),
                "sell_price": round(sell),
                "pnl": round(pnl, 6),
                "win": pnl > 0,
            })

    # Current signal using the last two candles
    current_signal = None
    if len(data) >= 2:
        prev = data[-2]
        curr = data[-1]
        prev_range = prev["high_price"] - prev["low_price"]
        target = curr["opening_price"] + k * prev_range
        current_signal = {
            "date": curr["candle_date_time_kst"][:10],
            "open": curr["opening_price"],
            "prev_range": round(prev_range),
            "target_price": round(target),
            "current_price": curr["trade_price"],
            "triggered": curr["high_price"] >= target,
            "k": k,
        }

    if not trades:
        return {
            "strategy": "K_VOLATILITY_BREAKOUT",
            "k": k,
            "total_candles": len(data),
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
        }

    wins = sum(1 for t in trades if t["win"])
    win_rate = wins / len(trades)
    avg_pnl = sum(t["pnl"] for t in trades) / len(trades)

    cumulative = 1.0
    equity_curve = []
    for t in trades:
        cumulative *= 1 + t["pnl"]
        equity_curve.append({
            "date": t["date"],
            "value": round(initial_capital * cumulative),
        })
    total_return = cumulative - 1
    final_value = round(initial_capital * cumulative)
    profit_loss = final_value - initial_capital

    # attach per-trade krw profit/loss
    portfolio = initial_capital
    for t in trades:
        prev_portfolio = portfolio
        portfolio = round(portfolio * (1 + t["pnl"]))
        t["krw_pnl"] = portfolio - prev_portfolio

    return {
        "strategy": "K_VOLATILITY_BREAKOUT",
        "k": k,
        "total_candles": len(data),
        "total_trades": len(trades),
        "win_rate": round(win_rate, 4),
        "avg_pnl_per_trade": round(avg_pnl, 6),
        "total_return": round(total_return, 4),
        "initial_capital": initial_capital,
        "final_value": final_value,
        "profit_loss": profit_loss,
        "equity_curve": equity_curve,
        "current_signal": current_signal,
        "trades": trades[-30:],
    }
