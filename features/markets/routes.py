from flask import Blueprint, jsonify, request, make_response
from .service import get_markets

markets_bp = Blueprint("markets", __name__, url_prefix="/api")


@markets_bp.route("/markets")
def markets():
    exchange = request.args.get("exchange", "upbit")
    data = get_markets(exchange)
    resp = make_response(jsonify(data))
    # 마켓 목록은 변경이 매우 드물어 5분 캐시
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp
