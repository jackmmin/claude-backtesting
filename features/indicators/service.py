import statistics
from exchanges import get_exchange


def get_indicators(exchange="upbit", market="KRW-BTC", count=200, interval="days"):
    exch = get_exchange(exchange)
    candles = exch.get_candles_bulk(market, count=count, interval=interval)

    if len(candles) < 15:
        return {"error": f"데이터 부족: {len(candles)}개 (최소 15개 필요)"}

    # 시간 오름차순 정렬
    data = list(reversed(candles))
    closes = [c["trade_price"] for c in data]
    volumes = [c["candle_acc_trade_volume"] for c in data]
    is_minute = interval.startswith("minutes")

    # 날짜 레이블 — 분봉은 전체 datetime, 일봉 이상은 날짜만
    labels = [
        c["candle_date_time_kst"] if is_minute else c["candle_date_time_kst"][:10]
        for c in data
    ]

    rsi_series = _calc_rsi_series(closes, period=14)
    volume_series = volumes

    return {
        "market": market,
        "interval": interval,
        "labels": labels,
        "rsi": rsi_series,       # 앞 14개는 None
        "volume": volume_series,
    }


def _calc_rsi_series(closes, period=14):
    """각 캔들 시점의 RSI 값 리스트 반환 (초기 period개는 None)"""
    result = [None] * period

    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))

    if len(gains) < period:
        return result + [None] * (len(closes) - period)

    # Wilder 스무딩 RSI
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _rsi_val(ag, al):
        if al == 0:
            return 100.0 if ag > 0 else 50.0
        return 100 - (100 / (1 + ag / al))

    result.append(_rsi_val(avg_gain, avg_loss))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        result.append(_rsi_val(avg_gain, avg_loss))

    return result
