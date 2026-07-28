import os
import io
import threading
from datetime import datetime, timedelta
import pytz
from flask import Flask, jsonify, request, render_template_string
from PIL import Image
import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import google.generativeai as genai
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

app = Flask(__name__)

# API Keys Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6KwuimLIB6Pgr3J6AcTmvEQl67nA2nVqjRwspe8Up4PVQ")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8790700892:AAHEY-R__HoauY2ftvYL_aWgWWfcQdOPgTw")

# Configure Gemini AI
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Gemini Init Error: {e}")

# Web Dashboard Currency Pairs
CURRENCY_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", 
    "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", 
    "AUDJPY", "EURCAD", "GBPCAD", "EURAUD", "AUDCAD",
    "BTCUSD", "ETHUSD", "XAUUSD"
]

YF_MAP = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X", "USDCAD": "CAD=X", "USDCHF": "CHF=X",
    "NZDUSD": "NZDUSD=X", "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X", "AUDJPY": "AUDJPY=X", "EURCAD": "EURCAD=X",
    "GBPCAD": "GBPCAD=X", "EURAUD": "EURAUD=X", "AUDCAD": "AUDCAD=X",
    "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD", "XAUUSD": "GC=F"
}

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live AI Market Signal</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Rajdhani', sans-serif; }
        body { background-color: #0b0e14; color: #e2e8f0; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 15px; }
        .dashboard { width: 100%; max-width: 420px; background: #131722; border: 1px solid #2a2e3d; border-radius: 20px; padding: 24px; box-shadow: 0 0 35px rgba(0, 231, 255, 0.1); }
        .header { text-align: center; margin-bottom: 20px; }
        .header h1 { font-family: 'Orbitron', sans-serif; font-size: 20px; color: #00e7ff; letter-spacing: 1.5px; text-shadow: 0 0 10px rgba(0, 231, 255, 0.5); }
        .header p { font-size: 12px; color: #787b86; margin-top: 4px; }
        .input-group { margin-bottom: 15px; }
        label { display: block; font-size: 13px; color: #9db2ce; margin-bottom: 6px; font-weight: 700; }
        select { width: 100%; padding: 12px; background: #1e222d; border: 1px solid #363c4e; border-radius: 10px; color: #fff; font-size: 15px; font-weight: bold; outline: none; }
        .btn-analyze { width: 100%; padding: 15px; background: linear-gradient(135deg, #0052d4, #4364f7, #6fb1fc); border: none; border-radius: 12px; color: white; font-family: 'Orbitron', sans-serif; font-size: 15px; font-weight: 800; cursor: pointer; margin-top: 10px; }
        .loader { display: none; text-align: center; margin: 20px 0; }
        .spinner { width: 35px; height: 35px; border: 4px solid #1e222d; border-top: 4px solid #00e7ff; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .result-box { display: none; margin-top: 22px; background: #1e222d; border-radius: 14px; padding: 18px; border: 1px solid #2a2e3d; }
        .signal-banner { text-align: center; padding: 14px; border-radius: 10px; margin-bottom: 15px; font-family: 'Orbitron', sans-serif; }
        .call-bg { background: rgba(8, 153, 129, 0.2); border: 2px solid #089981; color: #26a69a; }
        .put-bg { background: rgba(242, 54, 69, 0.2); border: 2px solid #f23645; color: #f23645; }
        .wait-bg { background: rgba(255, 179, 0, 0.2); border: 2px solid #ffb300; color: #ffb300; }
        .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #2a2e3d; font-size: 14px; }
        .val-highlight { font-weight: bold; color: #00e7ff; }
        .prob-badge { background: #00e7ff; color: #0b0e14; padding: 2px 8px; border-radius: 6px; font-weight: 800; }
    </style>
</head>
<body>
<div class="dashboard">
    <div class="header">
        <h1>LIVE MARKET AI</h1>
        <p>Real-Time Market Indicators & Analysis</p>
    </div>
    <div class="input-group">
        <label>SELECT LIVE ASSET</label>
        <select id="pairSelect">
            {% for pair in pairs %}
                <option value="{{ pair }}">{{ pair }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="input-group">
        <label>TIMEFRAME</label>
        <select id="tfSelect">
            <option value="1m">1 MINUTE</option>
            <option value="5m">5 MINUTES</option>
            <option value="15m">15 MINUTES</option>
        </select>
    </div>
    <button class="btn-analyze" onclick="getSignal()">ANALYZE LIVE MARKET</button>
    <div class="loader" id="loader">
        <div class="spinner"></div>
        <p style="font-size: 12px; color: #787b86; margin-top: 8px;">Analyzing Real-Time Candlestick Data...</p>
    </div>
    <div class="result-box" id="resultBox">
        <div class="signal-banner" id="signalBanner">
            <div style="font-size: 18px; font-weight: 800;" id="signalText">CALL</div>
        </div>
        <div class="info-row"><span>Asset:</span><span class="val-highlight" id="resPair">EURUSD</span></div>
        <div class="info-row"><span>Entry Time (UTC+6):</span><span class="val-highlight" id="resTime">--:--:--</span></div>
        <div class="info-row"><span>Live Price:</span><span class="val-highlight" id="resPrice">--</span></div>
        <div class="info-row"><span>RSI Value:</span><span class="val-highlight" id="resRsi">--</span></div>
        <div class="info-row"><span>Analysis Recommendation:</span><span class="prob-badge" id="resRec">--</span></div>
    </div>
</div>
<script>
    async function getSignal() {
        const pair = document.getElementById('pairSelect').value;
        const timeframe = document.getElementById('tfSelect').value;
        const loader = document.getElementById('loader');
        const resultBox = document.getElementById('resultBox');
        loader.style.display = 'block';
        resultBox.style.display = 'none';
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pair, timeframe })
            });
            const data = await response.json();
            loader.style.display = 'none';

            if(data.error) {
                alert('Market Error: ' + data.error);
                return;
            }

            resultBox.style.display = 'block';
            document.getElementById('resPair').innerText = data.pair;
            document.getElementById('resTime').innerText = data.entry_time;
            document.getElementById('resPrice').innerText = data.price;
            document.getElementById('resRsi').innerText = data.rsi;
            document.getElementById('resRec').innerText = data.recommendation;

            const banner = document.getElementById('signalBanner');
            const signalText = document.getElementById('signalText');

            if (data.direction === 'CALL') {
                banner.className = 'signal-banner call-bg';
                signalText.innerText = '🟢 NEXT CANDLE: GREEN (CALL)';
            } else if (data.direction === 'PUT') {
                banner.className = 'signal-banner put-bg';
                signalText.innerText = '🔴 NEXT CANDLE: RED (PUT)';
            } else {
                banner.className = 'signal-banner wait-bg';
                signalText.innerText = '⚠️ NO TRADE / NEUTRAL';
            }
        } catch (err) {
            alert('Error fetching signal. Try again!');
            loader.style.display = 'none';
        }
    }
</script>
</body>
</html>'''

def analyze_live_market(symbol, timeframe):
    try:
        yf_symbol = YF_MAP.get(symbol, f"{symbol}=X")
        tf_map = {"1m": "1m", "5m": "5m", "15m": "15m"}
        interval = tf_map.get(timeframe, "1m")
        period = "1d" if interval == "1m" else "5d"

        df = yf.download(tickers=yf_symbol, period=period, interval=interval, progress=False)
        
        if df.empty or len(df) < 15:
            return {"error": "Unable to fetch live price candles right now."}

        if isinstance(df.columns, pd.MultiIndex):
            close_series = df['Close'][yf_symbol]
        else:
            close_series = df['Close']

        close_series = close_series.dropna()

        rsi = RSIIndicator(close=close_series, window=14).rsi()
        ema = EMAIndicator(close=close_series, window=20).ema_indicator()

        latest_close = float(close_series.iloc[-1])
        latest_rsi = round(float(rsi.iloc[-1]), 2)
        latest_ema = float(ema.iloc[-1])

        if latest_rsi < 35 or (latest_close > latest_ema and latest_rsi < 55):
            direction = "CALL"
            rec = "STRONG BUY"
        elif latest_rsi > 65 or (latest_close < latest_ema and latest_rsi > 45):
            direction = "PUT"
            rec = "STRONG SELL"
        else:
            direction = "WAIT"
            rec = "NEUTRAL"

        bd_tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(bd_tz)
        tf_mins = 1 if timeframe == "1m" else (5 if timeframe == "5m" else 15)
        next_candle_time = (now + timedelta(minutes=tf_mins)).replace(second=0, microsecond=0)

        return {
            "pair": symbol,
            "timeframe": timeframe,
            "price": round(latest_close, 5),
            "entry_time": next_candle_time.strftime("%H:%M:%S"),
            "direction": direction,
            "recommendation": rec,
            "rsi": latest_rsi
        }
    except Exception as e:
        return {"error": str(e)}

# --- TELEGRAM BOT LOGIC ---
PROMPT = """
You are an expert Binary Options & Forex Technical Analysis Trader. 
Analyze the provided candlestick chart image very carefully.

Examine:
1. Candlestick patterns (e.g. Hammer, Shooting Star, Engulfing, Doji, Pinbar, Wicks).
2. Market Trend (Uptrend, Downtrend, or Sideways).
3. Support and Resistance levels / Rejection wicks.

Based on your analysis, predict the direction of the VERY NEXT CANDLE.

Respond strictly in this clean format:

📊 **CHART AI SIGNAL ANALYSIS**
---------------------------------
📈 **Trend:** [Uptrend / Downtrend / Sideways]
🔍 **Pattern Identified:** [Pattern Name]
🛡️ **Key Level:** [Near Support / Near Resistance / Neutral]
🎯 **Prediction (Next Candle):** [🟢 CALL (GREEN) / 🔴 PUT (RED) / ⚠️ NO TRADE]
🔥 **Confidence Score:** [e.g. 85%]
💡 **Reason:** [Brief 1-sentence reason]
"""

def handle_photo(update, context):
    try:
        update.message.reply_text("🔎 Analyzing your chart image with AI Vision... Please wait 5-10 seconds.")
        photo_file = update.message.photo[-1].get_file()
        photo_bytes = photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        response = model.generate_content([PROMPT, image])
        update.message.reply_text(response.text, parse_mode='Markdown')
    except Exception as e:
        update.message.reply_text(f"❌ Error analyzing image: {str(e)}")

def start(update, context):
    update.message.reply_text(
        "👋 Welcome to Chart Vision AI Bot!\n\n"
        "Send me a clean screenshot of any Candlestick Chart (Quotex, Pocket Option, TradingView, OTC or Live).\n"
        "I will scan the patterns and predict the next candle direction for you! 🚀"
    )

def run_telegram_bot():
    try:
        updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.photo, handle_photo))
        updater.start_polling(drop_pending_updates=True)
        print("Telegram Bot Active & Listening...")
    except Exception as e:
        print(f"Bot failed to start: {e}")

# Start Telegram bot in background thread
threading.Thread(target=run_telegram_bot, daemon=True).start()

# --- FLASK ROUTES ---
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, pairs=CURRENCY_PAIRS)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True) or {}
    pair = data.get('pair', 'EURUSD')
    timeframe = data.get('timeframe', '1m')
    result = analyze_live_market(pair, timeframe)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
