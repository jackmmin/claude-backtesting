import configparser
import os

_KEY_FILE = os.path.join(os.path.dirname(__file__), "..", "upbit_keys")


def _path():
    return os.path.abspath(_KEY_FILE)


def load_keys() -> dict:
    """upbit_keys 파일에서 3종 API 키를 읽어 반환"""
    cfg = configparser.ConfigParser()
    cfg.read(_path(), encoding="utf-8")
    return {
        "balance_access_key": cfg.get("balance", "access_key", fallback="").strip(),
        "balance_secret_key": cfg.get("balance", "secret_key", fallback="").strip(),
        "order_query_access_key": cfg.get("order_query", "access_key", fallback="").strip(),
        "order_query_secret_key": cfg.get("order_query", "secret_key", fallback="").strip(),
        "order_access_key": cfg.get("order", "access_key", fallback="").strip(),
        "order_secret_key": cfg.get("order", "secret_key", fallback="").strip(),
    }


def save_keys(balance_ak, balance_sk, order_query_ak, order_query_sk, order_ak, order_sk):
    """3종 API 키를 upbit_keys 파일에 저장"""
    cfg = configparser.ConfigParser()
    cfg["balance"] = {"access_key": balance_ak, "secret_key": balance_sk}
    cfg["order_query"] = {"access_key": order_query_ak, "secret_key": order_query_sk}
    cfg["order"] = {"access_key": order_ak, "secret_key": order_sk}
    with open(_path(), "w", encoding="utf-8") as f:
        f.write("# 업비트 API 키 설정 (이 파일은 GitHub에 업로드되지 않습니다)\n\n")
        cfg.write(f)


def has_keys() -> bool:
    """6개 키가 모두 설정되어 있는지 확인"""
    keys = load_keys()
    return all(v for v in keys.values())
