import requests

UPBIT_BASE = "https://api.upbit.com/v1"


def get(endpoint, params=None):
    res = requests.get(f"{UPBIT_BASE}{endpoint}", params=params, timeout=5)
    res.raise_for_status()
    return res.json()
