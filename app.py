from flask import Flask, render_template
from features.markets.routes import markets_bp
from features.candles.routes import candles_bp
from features.ticker.routes import ticker_bp

app = Flask(__name__)
app.register_blueprint(markets_bp)
app.register_blueprint(candles_bp)
app.register_blueprint(ticker_bp)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
