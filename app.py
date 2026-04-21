from flask import Flask, render_template
from features.markets.routes import markets_bp
from features.candles.routes import candles_bp
from features.ticker.routes import ticker_bp
from features.backtesting.routes import backtesting_bp
from features.signals.routes import signals_bp
from features.indicators.routes import indicators_bp
from features.trading.routes import trading_bp

app = Flask(__name__)
app.register_blueprint(markets_bp)
app.register_blueprint(candles_bp)
app.register_blueprint(ticker_bp)
app.register_blueprint(backtesting_bp)
app.register_blueprint(signals_bp)
app.register_blueprint(indicators_bp)
app.register_blueprint(trading_bp)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
