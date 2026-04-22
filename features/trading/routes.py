from flask import Blueprint, jsonify, request
from utils.key_config import load_keys, save_keys, has_keys, key_file_path
from exchanges.upbit import private_client as upbit
from .models import TradingConfig
from . import state_manager as sm
from . import scheduler as sch
from . import service as trading_service

trading_bp = Blueprint("trading", __name__, url_prefix="/api")


def _build_config(settings: dict) -> TradingConfig:
    """upbit_keys 파일의 키 + 설정값으로 TradingConfig 생성"""
    keys = load_keys()
    return TradingConfig(
        balance_access_key=keys["balance_access_key"],
        balance_secret_key=keys["balance_secret_key"],
        order_query_access_key=keys["order_query_access_key"],
        order_query_secret_key=keys["order_query_secret_key"],
        order_access_key=keys["order_access_key"],
        order_secret_key=keys["order_secret_key"],
        market=settings.get("market", "KRW-BTC"),
        strategy=settings.get("strategy", "K_VOLATILITY_BREAKOUT"),
        strategy_params=settings.get("strategy_params", {}),
        position_size_pct=float(settings.get("position_size_pct", 0.3)),
        timeframe=settings.get("timeframe", "days"),
        enabled=settings.get("enabled", False),
    )


def _test_all_keys(keys: dict) -> tuple[float | None, str | None]:
    """3종 API 키 연결 테스트. 성공 시 (KRW잔액, None), 실패 시 (None, 오류메시지)"""
    try:
        accounts = upbit.get_accounts(keys["balance_access_key"], keys["balance_secret_key"])
    except Exception as e:
        return None, f"자산조회 API 연결 실패: {e}"
    try:
        upbit.get_orders(keys["order_query_access_key"], keys["order_query_secret_key"], limit=1)
    except Exception as e:
        return None, f"주문조회 API 연결 실패: {e}"
    # 주문하기는 실제 주문 없이 인증만 검증 (최소금액 오류는 인증 성공으로 간주)
    try:
        upbit.post_order(keys["order_access_key"], keys["order_secret_key"],
                         market="KRW-BTC", side="bid", ord_type="price", price=1)
    except upbit.UpbitAPIError as e:
        if e.status_code == 401:
            return None, f"주문하기 API 연결 실패: {e}"
    except Exception as e:
        return None, f"주문하기 API 연결 실패: {e}"

    krw = next((a for a in accounts if a["currency"] == "KRW"), None)
    return float(krw["balance"]) if krw else 0, None


@trading_bp.route("/trading/keys", methods=["GET"])
def get_keys_status():
    """upbit_keys 파일의 섹션별 설정 여부 반환 (실제 키 값은 노출하지 않음)"""
    keys = load_keys()
    return jsonify({
        "has_balance": bool(keys["balance_access_key"] and keys["balance_secret_key"]),
        "has_order_query": bool(keys["order_query_access_key"] and keys["order_query_secret_key"]),
        "has_order": bool(keys["order_access_key"] and keys["order_secret_key"]),
        "has_all": has_keys(),
        "key_file": key_file_path(),
    })


@trading_bp.route("/trading/config", methods=["POST"])
def save_config():
    """API 키 3종 저장 (upbit_keys 파일) 및 매매 설정 저장.
    키 필드가 모두 비어있으면 upbit_keys 파일의 기존 값으로 연결 테스트."""
    data = request.json or {}
    input_keys = {
        "balance_access_key": data.get("balance_access_key", "").strip(),
        "balance_secret_key": data.get("balance_secret_key", "").strip(),
        "order_query_access_key": data.get("order_query_access_key", "").strip(),
        "order_query_secret_key": data.get("order_query_secret_key", "").strip(),
        "order_access_key": data.get("order_access_key", "").strip(),
        "order_secret_key": data.get("order_secret_key", "").strip(),
    }

    all_filled = all(input_keys.values())
    all_empty = not any(input_keys.values())

    if all_empty:
        # 필드 비어있음 → upbit_keys 파일 값으로 연결 테스트
        keys = load_keys()
        if not has_keys():
            return jsonify({"error": "upbit_keys 파일에 API 키가 설정되지 않았습니다"}), 400
    elif all_filled:
        keys = input_keys
        save_keys(
            keys["balance_access_key"], keys["balance_secret_key"],
            keys["order_query_access_key"], keys["order_query_secret_key"],
            keys["order_access_key"], keys["order_secret_key"],
        )
    else:
        return jsonify({"error": "API 키 3종(자산조회 / 주문조회 / 주문하기)을 모두 입력해주세요"}), 400

    balance, err = _test_all_keys(keys)
    if err:
        return jsonify({"error": err}), 401

    settings = {
        "market": data.get("market", "KRW-BTC"),
        "strategy": data.get("strategy", "K_VOLATILITY_BREAKOUT"),
        "strategy_params": data.get("strategy_params", {}),
        "position_size_pct": float(data.get("position_size_pct", 0.3)),
        "timeframe": data.get("timeframe", "days"),
        "enabled": False,
    }
    sm.save_config(settings)

    return jsonify({
        "success": True,
        "krw_balance": balance,
        "message": f"연결 성공! KRW 잔액: {balance:,.0f}원",
    })


@trading_bp.route("/trading/config", methods=["GET"])
def get_config():
    """저장된 설정 조회"""
    saved = sm.load_config()
    return jsonify({
        "config": saved,
        "has_keys": has_keys(),
    })


@trading_bp.route("/trading/start", methods=["POST"])
def start_trading():
    """자동매매 시작"""
    data = request.json or {}

    # 요청에 새 API 키가 있으면 upbit_keys 파일 업데이트
    new_keys = {
        "balance_access_key": data.get("balance_access_key", "").strip(),
        "balance_secret_key": data.get("balance_secret_key", "").strip(),
        "order_query_access_key": data.get("order_query_access_key", "").strip(),
        "order_query_secret_key": data.get("order_query_secret_key", "").strip(),
        "order_access_key": data.get("order_access_key", "").strip(),
        "order_secret_key": data.get("order_secret_key", "").strip(),
    }
    if all(new_keys.values()):
        _, err = _test_all_keys(new_keys)
        if err:
            return jsonify({"error": err}), 401
        save_keys(
            new_keys["balance_access_key"], new_keys["balance_secret_key"],
            new_keys["order_query_access_key"], new_keys["order_query_secret_key"],
            new_keys["order_access_key"], new_keys["order_secret_key"],
        )
    elif not has_keys():
        return jsonify({"error": "upbit_keys 파일에 API 키를 먼저 설정해주세요"}), 400

    saved = sm.load_config() or {}
    saved["market"] = data.get("market", saved.get("market", "KRW-BTC"))
    saved["strategy"] = data.get("strategy", saved.get("strategy", "K_VOLATILITY_BREAKOUT"))
    saved["strategy_params"] = data.get("strategy_params", saved.get("strategy_params", {}))
    saved["position_size_pct"] = float(data.get("position_size_pct", saved.get("position_size_pct", 0.3)))
    saved["timeframe"] = data.get("timeframe", saved.get("timeframe", "days"))
    saved["enabled"] = True
    sm.save_config(saved)

    config = _build_config(saved)

    # K변동성돌파 전략: 시작 시점 KRW 잔고를 초기비용으로 저장 (손실 시 재매수 방지)
    if saved.get("strategy") == "K_VOLATILITY_BREAKOUT":
        try:
            balance = trading_service.get_balance(config)
            sm.set_initial_capital(balance["krw_balance"])
        except Exception:
            pass

    sch.start_trading(config)

    return jsonify({
        "success": True,
        "market": config.market,
        "strategy": config.strategy,
        "timeframe": config.timeframe,
        "message": f"{config.market} 자동매매 시작",
    })


@trading_bp.route("/trading/stop", methods=["POST"])
def stop_trading():
    """자동매매 중지"""
    data = request.json or {}
    market = data.get("market")

    if not market:
        saved = sm.load_config()
        market = saved["market"] if saved else None

    if not market:
        return jsonify({"error": "마켓을 지정해주세요"}), 400

    sch.stop_trading(market)

    saved = sm.load_config()
    if saved and saved.get("market") == market:
        saved["enabled"] = False
        sm.save_config(saved)

    return jsonify({"success": True, "market": market, "message": f"{market} 자동매매 중지"})


@trading_bp.route("/trading/status", methods=["GET"])
def get_status():
    """현재 상태 조회 (포지션, 잔액, 스케줄러)"""
    saved = sm.load_config()
    auto_position = sm.get_position(source="auto")
    manual_position = sm.get_position(source="manual")
    scheduler_status = sch.get_status()

    pnl_info = None
    manual_pnl_info = None
    balance_info = None

    if saved and has_keys():
        from exchanges.upbit.ticker import get_ticker
        config = _build_config(saved)

        # 업비트 보유 코인 중 미추적 포지션을 수동 포지션으로 자동 등록
        trading_service.sync_untracked_positions(config)
        auto_position = sm.get_position(source="auto")
        manual_position = sm.get_position(source="manual")

        if auto_position:
            ticker = get_ticker(auto_position["market"])
            if ticker:
                pnl_info = trading_service.get_position_pnl(config, ticker[0]["trade_price"], source="auto")

        if manual_position:
            ticker = get_ticker(manual_position["market"])
            if ticker:
                manual_pnl_info = trading_service.get_position_pnl(config, ticker[0]["trade_price"], source="manual")

        try:
            balance_info = trading_service.get_balance(config)
        except Exception:
            balance_info = None

    return jsonify({
        "scheduler": scheduler_status,
        "auto_position": auto_position,
        "manual_position": manual_position,
        # 하위 호환: 자동 포지션을 position 필드로도 반환
        "position": auto_position,
        "pnl": pnl_info,
        "manual_pnl": manual_pnl_info,
        "balance": balance_info,
        "config": saved,
        "has_keys": has_keys(),
        "last_event": sm.get_last_event(),
    })


@trading_bp.route("/trading/position/manual", methods=["POST"])
def set_manual_position():
    """수동으로 진입한 포지션 등록"""
    data = request.json or {}
    required = ["market", "entry_price", "quantity", "entry_datetime"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"{f} 필드가 필요합니다"}), 400

    from .models import Position
    pos = Position(
        market=data["market"],
        entry_price=float(data["entry_price"]),
        entry_datetime=data["entry_datetime"],
        quantity=float(data["quantity"]),
        strategy=data.get("strategy", "MANUAL"),
        source="manual",
        strategy_params={},
        entry_order_uuid=data.get("order_uuid", ""),
    )
    sm.set_position(pos)
    return jsonify({"success": True, "manual_position": sm.get_position(source="manual")})


@trading_bp.route("/trading/position/manual", methods=["DELETE"])
def close_manual_position():
    """수동 포지션 청산 기록"""
    data = request.json or {}
    pos = sm.get_position(source="manual")
    if not pos:
        return jsonify({"error": "수동 포지션이 없습니다"}), 404

    sell_price = data.get("sell_price")
    if not sell_price:
        # 현재가로 청산
        from exchanges.upbit.ticker import get_ticker
        ticker = get_ticker(pos["market"])
        if not ticker:
            return jsonify({"error": "현재가 조회 실패"}), 500
        sell_price = ticker[0]["trade_price"]

    sm.close_position(
        float(sell_price),
        datetime.now().isoformat(),
        data.get("exit_reason", "manual_close"),
        source="manual",
    )
    return jsonify({"success": True})


@trading_bp.route("/trading/orders", methods=["GET"])
def get_orders():
    """로컬 주문 이력 조회"""
    limit = int(request.args.get("limit", 50))
    return jsonify({"orders": sm.get_orders(limit)})


@trading_bp.route("/trading/trades", methods=["GET"])
def get_trades():
    """완료된 거래 이력 조회"""
    limit = int(request.args.get("limit", 50))
    return jsonify({"trades": sm.get_trades(limit)})


@trading_bp.route("/trading/balance", methods=["GET"])
def get_balance():
    """현재 잔액 조회"""
    if not has_keys():
        return jsonify({"error": "upbit_keys 파일에 API 키가 설정되지 않았습니다"}), 400
    saved = sm.load_config() or {}
    try:
        config = _build_config(saved)
        return jsonify(trading_service.get_balance(config))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
