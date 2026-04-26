"""API 키 관리 및 설정 저장 라우트"""
from flask import Blueprint, jsonify, request
from utils.key_config import load_keys, save_keys, has_keys, key_file_path
from exchanges.upbit import private_client as upbit
from . import state_manager as sm

keys_bp = Blueprint("trading_keys", __name__, url_prefix="/api")


def _test_all_keys(keys: dict) -> tuple[float | None, str | None, dict]:
    """3종 API 키 연결 테스트.
    반환: (KRW잔액, 오류메시지, key_status)
    key_status: 각 키별 연결 성공 여부 {"balance": bool, "order_query": bool, "order": bool}
    """
    key_status = {"balance": False, "order_query": False, "order": False}
    try:
        accounts = upbit.get_accounts(keys["balance_access_key"], keys["balance_secret_key"])
        key_status["balance"] = True
    except Exception as e:
        return None, f"자산조회 API 연결 실패: {e}", key_status
    try:
        upbit.get_orders(keys["order_query_access_key"], keys["order_query_secret_key"], limit=1)
        key_status["order_query"] = True
    except Exception as e:
        return None, f"주문조회 API 연결 실패: {e}", key_status
    # 주문하기는 실제 주문 없이 인증만 검증 (최소금액 오류는 인증 성공으로 간주)
    try:
        upbit.post_order(keys["order_access_key"], keys["order_secret_key"],
                         market="KRW-BTC", side="bid", ord_type="price", price=1)
        key_status["order"] = True
    except upbit.UpbitAPIError as e:
        if e.status_code == 401:
            return None, f"주문하기 API 연결 실패: {e}", key_status
        key_status["order"] = True  # 401 아닌 오류(최소금액 등)는 인증 성공
    except Exception as e:
        return None, f"주문하기 API 연결 실패: {e}", key_status

    krw = next((a for a in accounts if a["currency"] == "KRW"), None)
    return float(krw["balance"]) if krw else 0, None, key_status


@keys_bp.route("/trading/keys", methods=["GET"])
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


@keys_bp.route("/trading/config", methods=["POST"])
def save_config():
    """API 키 3종 저장 및 매매 설정 저장.
    키 필드가 모두 비어있으면 upbit_keys 파일의 기존 값으로 연결 테스트.
    """
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
    all_empty  = not any(input_keys.values())

    if all_empty:
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

    balance, err, key_status = _test_all_keys(keys)
    if err:
        return jsonify({"error": err, "key_status": key_status}), 401

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
        "key_status": key_status,
    })


@keys_bp.route("/trading/config", methods=["GET"])
def get_config():
    """저장된 설정 조회"""
    saved = sm.load_config()
    return jsonify({
        "config": saved,
        "has_keys": has_keys(),
    })
