import json
import os
from datetime import datetime
from .models import Position, Order

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "trading_state.json")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "trading_config.json")

_EMPTY_STATE = {
    "version": "1.0",
    "current_position": None,
    "orders": [],
    "trades": [],
    "daily_trade_count": {},
}


def _read_state():
    path = os.path.abspath(STATE_PATH)
    if not os.path.exists(path):
        return dict(_EMPTY_STATE)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_state(state):
    state["last_updated"] = datetime.now().isoformat()
    with open(os.path.abspath(STATE_PATH), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_position() -> dict | None:
    return _read_state().get("current_position")


def set_position(position: Position):
    state = _read_state()
    state["current_position"] = {
        "market": position.market,
        "entry_price": position.entry_price,
        "entry_datetime": position.entry_datetime,
        "quantity": position.quantity,
        "strategy": position.strategy,
        "strategy_params": position.strategy_params,
        "entry_order_uuid": position.entry_order_uuid,
    }
    _write_state(state)


def close_position(sell_price: float, sell_datetime: str, exit_reason: str, order_uuid: str = ""):
    state = _read_state()
    pos = state.get("current_position")
    if pos:
        pnl_pct = (sell_price - pos["entry_price"]) / pos["entry_price"]
        state["trades"].append({
            "buy_datetime": pos["entry_datetime"],
            "buy_price": pos["entry_price"],
            "sell_datetime": sell_datetime,
            "sell_price": sell_price,
            "quantity": pos["quantity"],
            "pnl_pct": round(pnl_pct, 6),
            "pnl_krw": round(pos["quantity"] * (sell_price - pos["entry_price"])),
            "strategy": pos["strategy"],
            "exit_reason": exit_reason,
            "sell_order_uuid": order_uuid,
        })
    state["current_position"] = None
    _write_state(state)


def add_order(order: Order):
    state = _read_state()
    state["orders"].append({
        "order_uuid": order.order_uuid,
        "side": order.side,
        "market": order.market,
        "price": order.price,
        "volume": order.volume,
        "ord_type": order.ord_type,
        "status": order.status,
        "created_at": order.created_at,
        "executed_funds": order.executed_funds,
    })
    # 최근 200개만 유지
    state["orders"] = state["orders"][-200:]
    _write_state(state)


def get_orders(limit=50):
    return list(reversed(_read_state().get("orders", [])))[:limit]


def get_trades(limit=50):
    return list(reversed(_read_state().get("trades", [])))[:limit]


def get_daily_trade_count(date_str: str) -> int:
    return _read_state().get("daily_trade_count", {}).get(date_str, 0)


def increment_daily_trade_count(date_str: str):
    state = _read_state()
    counter = state.get("daily_trade_count", {})
    counter[date_str] = counter.get(date_str, 0) + 1
    state["daily_trade_count"] = counter
    _write_state(state)


def save_config(config_dict: dict):
    with open(os.path.abspath(CONFIG_PATH), "w", encoding="utf-8") as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=2)


def load_config() -> dict | None:
    path = os.path.abspath(CONFIG_PATH)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
