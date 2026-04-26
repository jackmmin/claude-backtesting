from datetime import datetime
from features.signals.service import calculate_signals
from exchanges.upbit import private_client as upbit
from . import state_manager as sm
from .models import Position, Order, TradingConfig

FEE_RATE = 0.0005  # 업비트 수수료 0.05%

MAX_POSITION_SIZE_PCT = 0.5
MAX_KRW_PER_TRADE = 50_000_000
MAX_DAILY_TRADES = 20


def _parse_balance(accounts: list) -> dict:
    """accounts 응답에서 잔액 dict 생성 (get_accounts 재호출 없이 재사용)"""
    krw = next((a for a in accounts if a["currency"] == "KRW"), None)
    return {
        "krw_balance": float(krw["balance"]) if krw else 0,
        "krw_locked": float(krw.get("locked", 0)) if krw else 0,
        "holdings": {
            a["currency"]: float(a["balance"])
            for a in accounts if a["currency"] != "KRW" and float(a["balance"]) > 0
        },
    }


def sync_untracked_positions(config: TradingConfig, accounts: list | None = None) -> tuple[list, list]:
    """업비트 보유 코인 중 auto/manual 포지션으로 미추적된 코인을 수동 포지션으로 자동 등록.
    accounts를 외부에서 전달하면 get_accounts를 재호출하지 않는다.
    반환: (등록된 마켓 목록, accounts)
    """
    if accounts is None:
        try:
            accounts = upbit.get_accounts(config.balance_access_key, config.balance_secret_key)
        except Exception:
            return [], []

    auto_pos   = sm.get_position(source="auto")
    manual_pos = sm.get_position(source="manual")

    tracked = set()
    if auto_pos:
        tracked.add(auto_pos["market"])
    if manual_pos:
        tracked.add(manual_pos["market"])

    registered = []
    for account in accounts:
        if account["currency"] == "KRW":
            continue
        total_qty = float(account.get("balance", 0)) + float(account.get("locked", 0))
        if total_qty <= 0:
            continue
        market = f"KRW-{account['currency']}"
        if market in tracked:
            continue
        avg_price = float(account.get("avg_buy_price", 0))
        if avg_price <= 0:
            continue
        # manual_position 슬롯이 비어있을 때만 등록
        if sm.get_position(source="manual"):
            break
        pos = Position(
            market=market,
            entry_price=avg_price,
            entry_datetime=datetime.now().isoformat(),
            quantity=total_qty,
            strategy="MANUAL",
            source="manual",
        )
        sm.set_position(pos)
        tracked.add(market)
        registered.append(market)

    return registered, accounts


def get_balance(config: TradingConfig, accounts: list | None = None) -> dict:
    """KRW 잔액 및 보유 코인 조회. accounts를 전달하면 get_accounts를 재호출하지 않는다."""
    if accounts is None:
        accounts = upbit.get_accounts(config.balance_access_key, config.balance_secret_key)
    return _parse_balance(accounts)


def get_position_pnl(config: TradingConfig, current_price: float, source: str = "auto") -> dict | None:
    """현재 포지션 미실현 손익 계산"""
    pos = sm.get_position(source=source)
    if not pos or pos["market"] != config.market:
        return None
    entry = pos["entry_price"]
    qty = pos["quantity"]
    pnl_pct = (current_price * (1 - FEE_RATE) - entry) / entry
    pnl_krw = qty * (current_price - entry / (1 + FEE_RATE))
    return {
        "entry_price": entry,
        "current_price": current_price,
        "quantity": qty,
        "unrealized_pnl_pct": round(pnl_pct, 6),
        "unrealized_pnl_krw": round(pnl_krw),
        "entry_datetime": pos["entry_datetime"],
        "strategy": pos["strategy"],
    }


def check_and_execute(config: TradingConfig) -> dict:
    """신호 체크 후 매수/매도 실행 (스케줄러가 주기적으로 호출)"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y-%m-%d")

    if sm.get_daily_trade_count(date_str) >= MAX_DAILY_TRADES:
        return {"status": "skipped", "reason": "일일 거래 한도 초과", "time": now_str}

    signals_data = calculate_signals(
        exchange="upbit",
        market=config.market,
        count=200,
        interval=config.timeframe,
    )

    if "error" in signals_data:
        return {"status": "error", "reason": signals_data["error"], "time": now_str}

    target = next(
        (s for s in signals_data["signals"] if s["strategy"] == config.strategy),
        None,
    )
    if not target:
        return {"status": "skipped", "reason": "전략 신호 없음", "time": now_str}

    position = sm.get_position(source="auto")

    if not position and target["triggered"]:
        return _execute_buy(config, date_str, now_str)

    if position and position["market"] == config.market:
        # 포지션 보유 중 매수 신호가 다시 발생하면 이벤트 기록
        if target["triggered"]:
            sm.set_last_event("position_exists", "현재 포지션이 존재합니다")
        return _check_exit(config, position, now_str)

    return {"status": "waiting", "triggered": target["triggered"], "time": now_str}


def _execute_buy(config: TradingConfig, date_str: str, now_str: str) -> dict:
    balance = get_balance(config)
    avail_krw = balance["krw_balance"]

    order_krw = avail_krw * min(config.position_size_pct, MAX_POSITION_SIZE_PCT)
    order_krw = min(order_krw, MAX_KRW_PER_TRADE)
    order_krw = round(order_krw)

    if order_krw < 5000:
        return {"status": "skipped", "reason": f"잔액 부족 (가용 {avail_krw:,.0f}원)", "time": now_str}

    result = upbit.post_order(
        config.order_access_key, config.order_secret_key,
        market=config.market, side="bid", ord_type="price", price=order_krw,
    )

    executed_volume = float(result.get("volume", 0) or 0)
    executed_funds = float(result.get("executed_funds", order_krw))
    avg_price = executed_funds / executed_volume if executed_volume > 0 else 0
    entry_price = avg_price * (1 + FEE_RATE)

    pos = Position(
        market=config.market,
        entry_price=entry_price,
        entry_datetime=datetime.now().isoformat(),
        quantity=executed_volume,
        strategy=config.strategy,
        source="auto",
        strategy_params=config.strategy_params,
        entry_order_uuid=result.get("uuid", ""),
    )
    sm.set_position(pos)
    sm.increment_daily_trade_count(date_str)
    sm.add_order(Order(
        order_uuid=result.get("uuid", ""),
        side="bid",
        market=config.market,
        price=avg_price,
        volume=executed_volume,
        ord_type="price",
        status=result.get("state", "done"),
        created_at=result.get("created_at", now_str),
        executed_funds=executed_funds,
    ))

    return {
        "status": "bought",
        "market": config.market,
        "strategy": config.strategy,
        "price": avg_price,
        "quantity": executed_volume,
        "order_krw": order_krw,
        "time": now_str,
    }


def _check_exit(config: TradingConfig, position: dict, now_str: str) -> dict:
    from exchanges.upbit.ticker import get_ticker
    ticker = get_ticker(config.market)
    if not ticker:
        return {"status": "error", "reason": "현재가 조회 실패", "time": now_str}

    current_price = ticker[0]["trade_price"]
    entry = position["entry_price"]
    pnl_pct = (current_price - entry) / entry

    params = config.strategy_params
    tp_key = {"K_VOLATILITY_BREAKOUT": "k_tp", "RSI_OVERSOLD_BOUNCE": "rsi_tp",
               "MA_GOLDEN_CROSS": "ma_tp", "BOLLINGER_BOUNCE": "bb_tp"}.get(config.strategy, "tp")
    sl_key = {"K_VOLATILITY_BREAKOUT": "k_sl", "RSI_OVERSOLD_BOUNCE": "rsi_sl",
               "MA_GOLDEN_CROSS": "ma_sl", "BOLLINGER_BOUNCE": "bb_sl"}.get(config.strategy, "sl")

    tp_pct = float(params.get(tp_key, 0.05))
    sl_pct = float(params.get(sl_key, -0.03))

    exit_reason = None
    if pnl_pct >= tp_pct:
        exit_reason = "take_profit"
    elif pnl_pct <= sl_pct:
        exit_reason = "stop_loss"

    if not exit_reason:
        pnl_info = get_position_pnl(config, current_price)
        return {"status": "holding", "pnl_pct": round(pnl_pct * 100, 2), "time": now_str, "pnl": pnl_info}

    return _execute_sell(config, position, current_price, exit_reason, now_str)


def _execute_sell(config: TradingConfig, position: dict, current_price: float, exit_reason: str, now_str: str) -> dict:
    qty = position["quantity"]
    result = upbit.post_order(
        config.order_access_key, config.order_secret_key,
        market=config.market, side="ask", ord_type="market", volume=qty,
    )

    executed_funds = float(result.get("executed_funds", current_price * qty))
    executed_volume = float(result.get("volume", qty))
    avg_sell_price = executed_funds / executed_volume if executed_volume > 0 else current_price
    sell_price_net = avg_sell_price * (1 - FEE_RATE)

    sm.close_position(sell_price_net, datetime.now().isoformat(), exit_reason, result.get("uuid", ""), source="auto")
    sm.add_order(Order(
        order_uuid=result.get("uuid", ""),
        side="ask",
        market=config.market,
        price=avg_sell_price,
        volume=executed_volume,
        ord_type="market",
        status=result.get("state", "done"),
        created_at=result.get("created_at", now_str),
        executed_funds=executed_funds,
    ))

    pnl_pct = (sell_price_net - position["entry_price"]) / position["entry_price"]
    return {
        "status": "sold",
        "market": config.market,
        "exit_reason": exit_reason,
        "sell_price": avg_sell_price,
        "pnl_pct": round(pnl_pct * 100, 2),
        "time": now_str,
    }
