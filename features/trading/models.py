from dataclasses import dataclass, field


@dataclass
class TradingConfig:
    # 자산조회 API 키
    balance_access_key: str
    balance_secret_key: str
    # 주문조회 API 키
    order_query_access_key: str
    order_query_secret_key: str
    # 주문하기 API 키
    order_access_key: str
    order_secret_key: str

    market: str
    strategy: str
    strategy_params: dict
    position_size_pct: float  # 0.0 ~ 0.5 (최대 50%)
    timeframe: str            # "days", "minutes60", 등
    enabled: bool = False


@dataclass
class Position:
    market: str
    entry_price: float        # 수수료 포함 진입가
    entry_datetime: str       # ISO 8601
    quantity: float           # 코인 수량
    strategy: str
    strategy_params: dict = field(default_factory=dict)
    entry_order_uuid: str = ""


@dataclass
class Order:
    order_uuid: str
    side: str                 # "bid" (매수) / "ask" (매도)
    market: str
    price: float
    volume: float
    ord_type: str             # "market" / "limit"
    status: str               # "done", "cancel", "wait"
    created_at: str
    executed_funds: float = 0.0
