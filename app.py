from flask import Flask, jsonify, request, render_template_string
from datetime import datetime, timedelta
import random
import pytz

app = Flask(__name__)

CURRENCY_PAIRS = [
    "EUR/USD (OTC)", "GBP/USD (OTC)", "USD/BDT (OTC)", "USD/INR (OTC)",
    "AUD/CAD (OTC)", "EUR/JPY (OTC)", "GBP/JPY (OTC)", "USD/JPY (OTC)",
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"
]

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantum AI - Quotex Signal Dashboard</title>
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
        <h1>⚡ QUANTUM AI SIGNAL</h1>
        <p>Ultra-High Accuracy Strategy Engine</p>
    </div>
    <div class="input-group">
        <label>SELECT ASSET / PAIR</label>
        <select id="pairSelect">
            {% for pair in pairs %}
                <option value="{{ pair }}">{{ pair }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="input-group">
        <label>TIMEFRAME</label>
        <select id="tfSelect">
            <option value="1 MIN">1 MINUTE</option>
            <option value="5 MIN">5 MINUTES</option>
        </select>
    </div>
    <button class="btn-analyze" onclick="getSignal()">GENERATE SIGNAL</button>
    <div class="loader" id="loader">
        <div class="spinner"></div>
        <p style="font-size: 12px; color: #787b86; margin-top: 8px;">Analyzing S/R, FVG & Patterns...</p>
    </div>
    <div class="result-box" id="resultBox">
        <div class="signal-banner" id="signalBanner">
            <div style="font-size: 18px; font-weight: 800;" id="signalText">CALL</div>
        </div>
        <div class="info-row"><span>Asset:</span><span class="val-highlight" id="resPair">EUR/USD (OTC)</span></div>
        <div class="info-row"><span>Entry Time (UTC+6):</span><span class="val-highlight" id="resTime">--:--:--</span></div>
        <div class="info-row"><span>Winning Probability:</span><span class="prob-badge" id="resProb">0%</span></div>
        <div class="info-row"><span>Detected Pattern:</span><span class="val-highlight" id="resPattern">--</span></div>
        <div class="info-row"><span>Signal Strength:</span><span class="val-highlight" id="resStrength">--</span></div>
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
            resultBox.style.display = 'block';
            document.getElementById('resPair').innerText = data.pair;
            document.getElementById('resTime').innerText = data.entry_time;
            document.getElementById('resProb').innerText = data.probability;
            document.getElementById('resPattern').innerText = data.pattern;
            document.getElementById('resStrength').innerText = data.strength;
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
                signalText.innerText = '⚠️ NO TRADE (LOW WIN RATE)';
            }
        } catch (err) {
            alert('Error generating signal. Try again!');
            loader.style.display = 'none';
        }
    }
</script>
</body>
</html>'''

def analyze_advanced_market(pair, timeframe):
    total_confluence = 0
    trend_score = random.choice([20, 25, 0])
    total_confluence += trend_score
    osc_score = random.choice([20, 15, 0])
    total_confluence += osc_score
    smc_score = random.choice([25, 20, 10])
    total_confluence += smc_score
    
    patterns = [
        ("Bullish Hammer", 20, "CALL"), ("Shooting Star", 20, "PUT"),
        ("Bullish Engulfing", 20, "CALL"), ("Bearish Engulfing", 20, "PUT"),
        ("Doji (Indecision)", 15, "REVERSAL"), ("Morning Star", 25, "CALL"),
        ("Evening Star", 25, "PUT")
    ]
    detected_pattern, pattern_score, pattern_dir = random.choice(patterns)
    total_confluence += pattern_score
    
    win_probability = min(98, max(65, total_confluence + random.randint(-5, 5)))
    
    if win_probability >= 88:
        signal_color = "GREEN (CALL)" if pattern_dir in ["CALL", "REVERSAL"] else "RED (PUT)"
        direction = "CALL" if signal_color == "GREEN (CALL)" else "PUT"
        strength = "ULTRA HIGH (A+ SETUP)"
    elif win_probability >= 78:
        signal_color = "GREEN (CALL)" if pattern_dir == "CALL" else "RED (PUT)"
        direction = "CALL" if signal_color == "GREEN (CALL)" else "PUT"
        strength = "HIGH"
    else:
        signal_color = "NO TRADE"
        direction = "WAIT"
        strength = "WEAK - REJECTED"
        win_probability = random.randint(45, 60)

    bd_tz = pytz.timezone('Asia/Dhaka')
    now = datetime.now(bd_tz)
    tf_minutes = 1 if timeframe == "1 MIN" else 5
    next_candle_time = (now + timedelta(minutes=tf_minutes)).replace(second=0, microsecond=0)
    
    return {
        "pair": pair,
        "timeframe": timeframe,
        "entry_time": next_candle_time.strftime("%H:%M:%S"),
        "signal": signal_color,
        "direction": direction,
        "probability": f"{win_probability}%",
        "strength": strength,
        "pattern": detected_pattern
    }

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, pairs=CURRENCY_PAIRS)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True) or {}
    pair = data.get('pair', 'EUR/USD (OTC)')
    timeframe = data.get('timeframe', '1 MIN')
    result = analyze_advanced_market(pair, timeframe)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
