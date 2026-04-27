import requests
from urllib.parse import urlencode
from .auth import get_auth_headers

BASE_URL = "https://api.upbit.com/v1"

# 인증 요청용 세션 — Authorization 헤더는 요청마다 달라지므로 여기선 설정하지 않음
_session = requests.Session()


class UpbitAPIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _request(method, path, access_key, secret_key, params=None):
    query_string = urlencode(params) if params else ""
    headers = get_auth_headers(access_key, secret_key, query_string)
    url = f"{BASE_URL}{path}"

    if method == "GET":
        resp = _session.get(url, params=params, headers=headers, timeout=10)
    elif method == "POST":
        resp = _session.post(url, json=params, headers=headers, timeout=10)
    elif method == "DELETE":
        resp = _session.delete(url, params=params, headers=headers, timeout=10)
    else:
        raise ValueError(f"Unsupported method: {method}")

    if not resp.ok:
        error = resp.json().get("error", {})
        raise UpbitAPIError(error.get("message", resp.text), resp.status_code)

    return resp.json()


def get_accounts(access_key, secret_key):
    """계좌 잔액 조회 (자산조회 API 키 사용)"""
    return _request("GET", "/accounts", access_key, secret_key)


def post_order(access_key, secret_key, market, side, ord_type, volume=None, price=None):
    """주문 실행 (주문하기 API 키 사용)
    - side: "bid" (매수) / "ask" (매도)
    - ord_type: "price" (시장가 매수) / "market" (시장가 매도) / "limit" (지정가)
    """
    params = {"market": market, "side": side, "ord_type": ord_type}
    if volume is not None:
        params["volume"] = str(volume)
    if price is not None:
        params["price"] = str(price)
    return _request("POST", "/orders", access_key, secret_key, params)


def get_orders(access_key, secret_key, market=None, state="done", limit=50):
    """주문 이력 조회 (주문조회 API 키 사용)"""
    params = {"state": state, "limit": limit}
    if market:
        params["market"] = market
    return _request("GET", "/orders/closed", access_key, secret_key, params)


def get_order(access_key, secret_key, order_uuid):
    """단일 주문 상태 조회 (주문조회 API 키 사용)"""
    return _request("GET", "/order", access_key, secret_key, {"uuid": order_uuid})


def cancel_order(access_key, secret_key, order_uuid):
    """주문 취소 (주문하기 API 키 사용)"""
    return _request("DELETE", "/order", access_key, secret_key, {"uuid": order_uuid})
