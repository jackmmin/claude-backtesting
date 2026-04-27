import requests

UPBIT_BASE = "https://api.upbit.com/v1"

# TCP 연결 재사용으로 레이턴시 감소 — 스레드 안전하지 않으므로 모듈 레벨 단일 세션 사용
_session = requests.Session()
_session.headers.update({"Accept": "application/json"})


def get(endpoint, params=None):
    res = _session.get(f"{UPBIT_BASE}{endpoint}", params=params, timeout=5)
    res.raise_for_status()
    return res.json()
