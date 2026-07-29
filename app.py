import os
import pytz
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string, request
import pandas as pd
import numpy as np
import yfinance as yf

# Technical Indicators
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands

app = Flask(__name__)

CURRENCY_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", 
    "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", 
    "BTCUSD", "ETHUSD", "XAUUSD"
]

YF_MAP = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X", "USDCAD": "CAD=X", "USDCHF": "CHF=X",
    "NZDUSD": "NZDUSD=X", "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X", "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD", "XAUUSD": "GC=F"
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real Market Signal AI - Pro Glassmorphic UI</title>
    <!-- Premium Fonts Import -->
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {
            --bg-dark: #050811;
            --card-bg: rgba(15, 23, 42, 0.75);
            --card-border: rgba(0, 242, 254, 0.18);
            --neon-cyan: #00f2fe;
            --neon-blue: #4facfe;
            --green-glow: #00e676;
            --red-glow: #ff1744;
            --amber-glow: #ffab00;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px 12px;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(0, 242, 254, 0.08) 0%, transparent 45%),
                radial-gradient(circle at 85% 85%, rgba(79, 172, 254, 0.08) 0%, transparent 45%);
        }

        .container {
            width: 100%;
            max-width: 450px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 28px 22px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 25px rgba(0, 242, 254, 0.1);
            backdrop-filter: blur(16px);
            position: relative;
            overflow: hidden;
        }

        .container::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, #00f2fe, #4facfe, #00e676);
        }

        .header {
            text-align: center;
            margin-bottom: 22px;
        }

        .badge-live {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(0, 230, 118, 0.1);
            border: 1px solid rgba(0, 230, 118, 0.3);
            color: var(--green-glow);
            padding: 5px 14px;
            border-radius: 20px;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }

        .dot {
            width: 7px; height: 7px;
            background-color: var(--green-glow);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--green-glow);
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { opacity: 0.3; }
            50% { opacity: 1; }
            100% { opacity: 0.3; }
        }

        .header h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 21px;
            font-weight: 900;
            background: linear-gradient(135deg, #ffffff 0%, #00f2fe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        .header p {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-sub);
            letter-spacing: 0.8px;
            margin-top: 6px;
            text-transform: uppercase;
        }

        .form-group {
            margin-bottom: 16px;
        }

        .form-group label {
            display: block;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 11px;
            font-weight: 700;
            color: var(--text-sub);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .select-box {
            width: 100%;
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 14px;
            color: #fff;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 15px;
            font-weight: 700;
            outline: none;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .select-box:focus {
            border-color: var(--neon-cyan);
            box-shadow: 0 0 15px rgba(0, 242, 254, 0.25);
            background: rgba(255, 255, 255, 0.07);
        }

        .select-box option {
            background: #0f172a;
            color: #fff;
        }

        .btn-analyze {
            width: 100%;
            padding: 16px;
            margin-top: 10px;
            background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            border: none;
            border-radius: 14px;
            color: #030712;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(0, 242, 254, 0.35);
        }

        .btn-analyze:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(0, 242, 254, 0.55);
            filter: brightness(1.1);
        }

        .loader {
            display: none;
            text-align: center;
            padding: 25px 0;
        }

        .spinner {
            width: 42px; height: 42px;
            border: 4px solid rgba(255, 255, 255, 0.05);
            border-top: 4px solid var(--neon-cyan);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .result-card {
            display: none;
            margin-top: 22px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 20px;
            animation: fadeIn 0.4s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .signal-box {
            text-align: center;
            padding: 18px;
            border-radius: 14px;
            margin-bottom: 18px;
            font-family: 'Orbitron', sans-serif;
            font-weight: 900;
            letter-spacing: 1.5px;
            text-shadow: 0 0 12px currentColor;
        }

        .signal-call {
            background: rgba(0, 230, 118, 0.12);
            border: 2px solid var(--green-glow);
            color: var(--green-glow);
        }

        .signal-put {
            background: rgba(255, 23, 68, 0.12);
            border: 2px solid var(--red-glow);
            color: var(--red-glow);
        }

        .signal-wait {
            background: rgba(255, 171, 0, 0.12);
            border: 2px solid var(--amber-glow);
            color: var(--amber-glow);
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        }

        .metric-box {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 12px;
            border-radius: 12px;
            text-align: center;
        }

        .metric-label {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 10px;
            color: var(--text-sub);
            font-weight: 700;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .metric-value {
            font-family: 'Orbitron', sans-serif;
            font-size: 14px;
            font-weight: 800;
            color: #fff;
            letter-spacing: 0.5px;
        }

        .accuracy-badge {
            display: inline-block;
            background: linear-gradient(135deg, #00f2fe, #4facfe);
            color: #000;
            padding: 2px 10px;
            border-radius: 20px;
            font-family: 'Orbitron', sans-serif;
            font-size: 13px;
            font-weight: 900;
        }

        .reason-card {
            background: rgba(0, 0, 0, 0.35);
            border-left: 3px solid var(--neon-cyan);
            border-radius: 10px;
            padding: 12px 14px;
            font-size: 12px;
            line-height: 1.6;
            color: #cbd5e1;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        .reason-card strong {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 11px;
            letter-spacing: 0.8px;
            color: var(--neon-cyan);
        }

        .footer-note {
            text-align: center;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 11px;
            font-weight: 600;
            color: #475569;
            margin-top: 20px;
            letter-spacing: 0.5px;
        }
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <div class="badge-live"><span class="dot"></span> 4-Layer Institutional Logic</div>
        <h1>REAL MARKET SIGNAL AI</h1>
        <p>Advanced Algorithmic Confluence Engine</p>
    </div>

    <div class="form-group">
        <label>SELECT ASSET PAIR</label>
        <select id="pairSelect" class="select-box">
            {% for pair in pairs %}
                <option value="{{ pair }}">{{ pair }}</option>
            {% endfor %}
        </select>
    </div>

    <div class="form-group">
        <label>SELECT TIMEFRAME</label>
        <select id="tfSelect" class="select-box">
            <option value="1m">1 MINUTE</option>
            <option value="5m">5 MINUTES</option>
            <option value="15m">15 MINUTES</option>
        </select>
    </div>

    <button class="btn-analyze" onclick="getSignal()">ANALYZE SIGNAL</button>

    <div class="loader" id="loader">
        <div class="spinner"></div>
        <p style="font-family: 'Space Grotesk', sans-serif; font-size: 12px; color: var(--text-sub); margin-top: 12px; font-weight: 600; letter-spacing: 0.5px;">
            Scanning 4-Layer Institutional Logic...
        </p>
    </div>

    <div class="result-card" id="resultCard">
        <div class="signal-box" id="signalBox">
            <div style="font-size: 18px;" id="signalText">CALL</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-box">
                <div class="metric-label">ENTRY TIME (BD)</div>
                <div class="metric-value" id="resTime">--:--:--</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">ACCURACY SCORE</div>
                <div class="metric-value"><span class="accuracy-badge" id="resScore">0%</span></div>
            </div>
            <div class="metric-box">
                <div class="metric-label">LIVE PRICE</div>
                <div class="metric-value" id="resPrice" style="color: var(--neon-cyan);">--</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">FILTER STATUS</div>
                <div class="metric-value" id="resStatus" style="font-size: 12px; font-family: 'Space Grotesk', sans-serif; font-weight: 700;">--</div>
            </div>
        </div>

        <div class="reason-card" id="resReason">
            Analysis Summary...
        </div>
    </div>

    <div class="footer-note">
        ⚠️ Strict Filter: Trades auto-pause if confluence is below 75%.
    </div>
</div>

<script>
    // Initialize Telegram WebApp SDK
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }

    async function getSignal() {
        const pair = document.getElementById('pairSelect').value;
        const timeframe = document.getElementById('tfSelect').value;
        const loader = document.getElementById('loader');
        const resultCard = document.getElementById('resultCard');
        
        loader.style.display = 'block';
        resultCard.style.display = 'none';
        
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pair, timeframe })
            });
            
            const data = await response.json();
            loader.style.display = 'none';
            
            if(data.error) {
                alert('Market Data Error: ' + data.error);
                return;
            }
            
            resultCard.style.display = 'block';
            document.getElementById('resTime').innerText = data.entry_time;
            document.getElementById('resPrice').innerText = data.price;
            document.getElementById('resStatus').innerText = data.status;
            document.getElementById('resScore').innerText = data.confidence + '%';
            document.getElementById('resReason').innerHTML = '<strong>LOGICAL ANALYSIS SUMMARY:</strong><br>' + data.reason;
            
            const signalBox = document.getElementById('signalBox');
            const signalText = document.getElementById('signalText');
            
            if (data.direction === 'CALL') {
                signalBox.className = 'signal-box signal-call';
                signalText.innerText = '🟢 NEXT CANDLE: CALL (BUY)';
            } else if (data.direction === 'PUT') {
                signalBox.className = 'signal-box signal-put';
                signalText.innerText = '🔴 NEXT CANDLE: PUT (SELL)';
            } else {
                signalBox.className = 'signal-box signal-wait';
                signalText.innerText = '⚠️ NO TRADE / WAIT';
            }
        } catch (err) {
            alert('Server connection error!');
            loader.style.display = 'none';
        }
    }
</script>

</body>
</html>"""

def perform_4layer_analysis(symbol, timeframe):
    try:
        yf_symbol = YF_MAP.get(symbol, f"{symbol}=X")
        tf_map = {"1m": "1m", "5m": "5m", "15m": "15m"}
        interval = tf_map.get(timeframe, "1m")
        period = "1d" if interval == "1m" else "5d"

        df = yf.download(tickers=yf_symbol, period=period, interval=interval, progress=False)
        if df.empty or len(df) < 50:
            return {"error": "Insufficient candlestick data found."}

        if isinstance(df.columns, pd.MultiIndex):
            df = df.xs(yf_symbol, axis=1, level=1)
        df = df.dropna()

        # --- 4-LAYER INDICATOR LOGIC ---
        
        # Layer 1: EMA 20/50 Tracker
        ema20 = EMAIndicator(close=df['Close'], window=20).ema_indicator().iloc[-1]
        ema50 = EMAIndicator(close=df['Close'], window=50).ema_indicator().iloc[-1]
        
        # Layer 2: Swing High / Swing Low (50 candles) Support & Resistance
        recent_high = float(df['High'].iloc[-50:-1].max())
        recent_low = float(df['Low'].iloc[-50:-1].min())
        curr_close = float(df['Close'].iloc[-1])
        curr_open = float(df['Open'].iloc[-1])
        curr_high = float(df['High'].iloc[-1])
        curr_low = float(df['Low'].iloc[-1])
        
        prev_open = float(df['Open'].iloc[-2])
        prev_close = float(df['Close'].iloc[-2])

        near_support = abs(curr_close - recent_low) / recent_low < 0.002
        near_resistance = abs(curr_close - recent_high) / recent_high < 0.002

        # Layer 3: Candlestick Pattern Detector
        body_size = abs(curr_close - curr_open)
        upper_wick = curr_high - max(curr_open, curr_close)
        lower_wick = min(curr_open, curr_close) - curr_low

        is_bull_engulfing = (curr_close > curr_open) and (prev_close < prev_open) and (curr_close > prev_open)
        is_bear_engulfing = (curr_close < curr_open) and (prev_close > prev_open) and (curr_close < prev_open)
        is_hammer = (lower_wick > 2 * body_size) and (upper_wick < body_size)
        is_star = (upper_wick > 2 * body_size) and (lower_wick < body_size)

        # Layer 4: RSI + Bollinger Bands
        rsi = RSIIndicator(close=df['Close'], window=14).rsi().iloc[-1]
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
        bb_lower = bb.bollinger_lband().iloc[-1]
        bb_upper = bb.bollinger_hband().iloc[-1]

        call_score = 0
        put_score = 0
        reasons = []

        # Layer 1 Scoring (25%)
        if ema20 > ema50:
            call_score += 25
            reasons.append("Market is in Uptrend based on EMA 20/50")
        else:
            put_score += 25
            reasons.append("Market is in Downtrend based on EMA 20/50")

        # Layer 2 Scoring (25%)
        if near_support:
            call_score += 25
            reasons.append("Price rejected from Major Support Level (Swing Low)")
        if near_resistance:
            put_score += 25
            reasons.append("Price rejected from Major Resistance Level (Swing High)")

        # Layer 3 Scoring (25%)
        if is_bull_engulfing or is_hammer:
            call_score += 25
            reasons.append("Bullish Reversal Pattern formed (Bullish Engulfing/Hammer)")
        if is_bear_engulfing or is_star:
            put_score += 25
            reasons.append("Bearish Reversal Pattern formed (Bearish Engulfing/Shooting Star)")

        # Layer 4 Scoring (25%)
        if rsi < 38 or curr_close <= bb_lower:
            call_score += 25
            reasons.append("RSI Oversold zone or Bollinger Bands lower band support")
        if rsi > 62 or curr_close >= bb_upper:
            put_score += 25
            reasons.append("RSI Overbought zone or Bollinger Bands upper band resistance")

        # Confluence Filter Rule (75%)
        if call_score >= 75 and call_score > put_score:
            direction = "CALL"
            confidence = min(call_score + 10, 96)
            status = "PASSED (75%+)"
            final_reason = " • ".join(reasons)
        elif put_score >= 75 and put_score > call_score:
            direction = "PUT"
            confidence = min(put_score + 10, 96)
            status = "PASSED (75%+)"
            final_reason = " • ".join(reasons)
        else:
            direction = "WAIT"
            confidence = max(call_score, put_score)
            status = "FILTERED (<75%)"
            final_reason = "75% confluence not met across 4-layer logic. Trade paused to preserve capital."

        bd_tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(bd_tz)
        tf_mins = 1 if timeframe == "1m" else (5 if timeframe == "5m" else 15)
        next_candle_time = (now + timedelta(minutes=tf_mins)).replace(second=0, microsecond=0)

        return {
            "pair": symbol,
            "timeframe": timeframe,
            "price": round(curr_close, 5),
            "entry_time": next_candle_time.strftime("%H:%M:%S"),
            "direction": direction,
            "confidence": confidence,
            "status": status,
            "reason": final_reason
        }
    except Exception as e:
        return {"error": str(e)}

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, pairs=CURRENCY_PAIRS)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True) or {}
    pair = data.get('pair', 'EURUSD')
    timeframe = data.get('timeframe', '1m')
    result = perform_4layer_analysis(pair, timeframe)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
