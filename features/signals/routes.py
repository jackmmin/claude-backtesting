import logging
from flask import Blueprint, jsonify, request
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
        return jsonify(calculate_signals(exchange, market, count, interval))
    except Exception as e:
        logger.error("신호 계산 오류", exc_info=True)
        return jsonify({"error": f"신호 계산 중 오류가 발생했습니다: {e}"}), 500
