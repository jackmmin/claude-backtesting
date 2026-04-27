import logging
from flask import Blueprint, jsonify, request, make_response
from .service import calculate_signals

signals_bp = Blueprint("signals", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


@signals_bp.route("/signals")
def signals():
    try:
        exchange = request.args.get("exchange", "upbit")
        market   = request.args.get("market", "KRW-BTC")
        interval = request.args.get("interval", "days")
        try:
            count = min(int(request.args.get("count", 200)), 1000)
        except (ValueError, TypeError):
            count = 200
        data = calculate_signals(exchange, market, count, interval)
        resp = make_response(jsonify(data))
        # 신호 데이터는 봉 마감 후 갱신되므로 30초 캐시
        resp.headers["Cache-Control"] = "public, max-age=30"
        return resp
    except Exception as e:
        logger.error("신호 계산 오류", exc_info=True)
        return jsonify({"error": f"신호 계산 중 오류가 발생했습니다: {e}"}), 500
