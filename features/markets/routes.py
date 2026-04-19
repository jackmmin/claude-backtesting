from flask import Blueprint, jsonify, request
from .service import get_markets

markets_bp = Blueprint("markets", __name__, url_prefix="/api")


@markets_bp.route("/markets")
def markets():
    exchange = request.args.get("exchange", "upbit")
    return jsonify(get_markets(exchange))
