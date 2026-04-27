from flask import Flask, render_template
from features.markets.routes import markets_bp
from features.candles.routes import candles_bp
from features.ticker.routes import ticker_bp
from features.backtesting.routes import backtesting_bp
from features.signals.routes import signals_bp
from features.indicators.routes import indicators_bp
from features.trading.routes import keys_bp, trading_bp

app = Flask(__name__)
app.register_blueprint(markets_bp)
app.register_blueprint(candles_bp)
app.register_blueprint(ticker_bp)
app.register_blueprint(backtesting_bp)
app.register_blueprint(signals_bp)
app.register_blueprint(indicators_bp)
app.register_blueprint(keys_bp)
app.register_blueprint(trading_bp)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    # DEPLOY_MODE=cloud 환경변수가 설정된 경우 클라우드 모드로 실행
    import os
    is_cloud = os.environ.get("DEPLOY_MODE") == "cloud"
    app.run(
        debug=not is_cloud,
        host="0.0.0.0" if is_cloud else "127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
    )
