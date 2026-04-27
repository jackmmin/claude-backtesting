import json
import os
from datetime import datetime
from .models import Position, Order

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "trading_state.json")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "trading_config.json")

_EMPTY_STATE = {
    "version": "1.1",
    "auto_position": None,
    "manual_position": None,
    "orders": [],
    "trades": [],
    "daily_trade_count": {},
    "initial_capital": None,
    "last_event": None,
}

# 메모리 캐시 — 파일 읽기를 최소화
_state_cache: dict | None = None
_config_cache: dict | None = None


def _read_state() -> dict:
    global _state_cache
    if _state_cache is not None:
        return _state_cache

    path = os.path.abspath(STATE_PATH)
    if not os.path.exists(path):
        _state_cache = dict(_EMPTY_STATE)
        return _state_cache

    with open(path, "r", encoding="utf-8") as f:
        state = json.load(f)

    # v1.0 → v1.1 마이그레이션: current_position → auto_position
    if "current_position" in state and "auto_position" not in state:
        state["auto_position"] = state.pop("current_position")
        state["manual_position"] = None
        state["version"] = "1.1"

    _state_cache = state
    return _state_cache


def _write_state(state: dict):
    global _state_cache
    state["last_updated"] = datetime.now().isoformat()
    with open(os.path.abspath(STATE_PATH), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    _state_cache = state  # 캐시 갱신


def get_position(source: str = "auto") -> dict | None:
    key = "auto_position" if source == "auto" else "manual_position"
    return _read_state().get(key)


def set_position(position: Position):
    state = _read_state()
    key = "auto_position" if position.source == "auto" else "manual_position"
    state[key] = {
        "market": position.market,
        "entry_price": position.entry_price,
        "entry_datetime": position.entry_datetime,
        "quantity": position.quantity,
        "strategy": position.strategy,
        "source": position.source,
        "strategy_params": position.strategy_params,
        "entry_order_uuid": position.entry_order_uuid,
        "entry_seed": position.entry_seed,
    }
    _write_state(state)


def close_position(sell_price: float, sell_datetime: str, exit_reason: str, order_uuid: str = "", source: str = "auto"):
    state = _read_state()
    key = "auto_position" if source == "auto" else "manual_position"
    pos = state.get(key)
    if pos:
        entry_seed = pos.get("entry_seed", 0.0)
        qty = pos["quantity"]
        pnl_pct = (sell_price - pos["entry_price"]) / pos["entry_price"]
        # 실제 수수료: 매수 시 (entry_price - raw_price)*qty + 매도 시 sell_raw*qty*fee_rate 를
        # 근사값으로 entry_seed * 0.0005 * 2 (업비트 단방향 0.05% × 2회)
        fee = round(entry_seed * 0.001)
        pnl_krw = round(qty * (sell_price - pos["entry_price"]))
        seed_after = round(entry_seed + pnl_krw)
        state["trades"].append({
            "buy_datetime": pos["entry_datetime"],
            "buy_price": pos["entry_price"],
            "sell_datetime": sell_datetime,
            "sell_price": sell_price,
            "quantity": qty,
            "entry_seed": entry_seed,
            "fee": fee,
            "pnl_pct": round(pnl_pct, 6),
            "pnl_krw": pnl_krw,
            "seed_after": seed_after,
            "strategy": pos["strategy"],
            "source": pos.get("source", source),
            "exit_reason": exit_reason,
            "sell_order_uuid": order_uuid,
        })
    state[key] = None
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


def set_initial_capital(amount: float):
    state = _read_state()
    state["initial_capital"] = amount
    _write_state(state)


def get_initial_capital() -> float | None:
    return _read_state().get("initial_capital")


def set_last_event(event_type: str, message: str):
    state = _read_state()
    state["last_event"] = {
        "type": event_type,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }
    _write_state(state)


def get_last_event() -> dict | None:
    return _read_state().get("last_event")


def get_daily_trade_count(date_str: str) -> int:
    return _read_state().get("daily_trade_count", {}).get(date_str, 0)


def increment_daily_trade_count(date_str: str):
    state = _read_state()
    counter = state.get("daily_trade_count", {})
    counter[date_str] = counter.get(date_str, 0) + 1
    state["daily_trade_count"] = counter
    _write_state(state)


def save_config(config_dict: dict):
    global _config_cache
    with open(os.path.abspath(CONFIG_PATH), "w", encoding="utf-8") as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=2)
    _config_cache = config_dict


def load_config() -> dict | None:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    path = os.path.abspath(CONFIG_PATH)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        _config_cache = json.load(f)
    return _config_cache
