import datetime
import threading
import time
from flask import Flask, jsonify, render_template, request
import requests
import yfinance as yf

# ==========================================
# 1. FLASK APPLICATION INITIALIZATION
# ==========================================
app = Flask(__name__)

# Global cache for Sensex live data
sensex_data_cache = {
    "price": "72,472.33",
    "change": "+879.09 pts",
    "p_change": "(+1.23%)",
    "is_positive": True,
    "timestamp": datetime.datetime.now().strftime("%b %d, %Y, %I:%M:%S %p"),
}


# ==========================================
# 2. ROBUST LIVE SENSEX FETCHER
# ==========================================
def fetch_live_sensex():
  """Fetches live Sensex price using multiple fallbacks to prevent cloud blocking."""
  # Attempt 1: Yahoo Finance API direct endpoint
  try:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EBSESN?interval=1m&range=1d"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=5)
    if resp.status_code == 200:
      meta = resp.json()["chart"]["result"][0]["meta"]
      price = meta.get("regularMarketPrice")
      prev_close = meta.get("chartPreviousClose")
      if price and prev_close:
        change = round(price - prev_close, 2)
        p_change = round((change / prev_close) * 100, 2)
        return {
            "price": f"{price:,.2f}",
            "change": f"{'+' if change >= 0 else ''}{change:,.2f} pts",
            "p_change": f"({'+' if p_change >= 0 else ''}{p_change:.2f}%)",
            "is_positive": change >= 0,
            "timestamp": datetime.datetime.now().strftime(
                "%b %d, %Y, %I:%M:%S %p"
            ),
        }
  except Exception as e:
    print(f"Direct API fetch error: {e}")

  # Attempt 2: yfinance fallback
  try:
    ticker = yf.Ticker("^BSESN")
    data = ticker.history(period="1d")
    if not data.empty:
      price = round(data["Close"].iloc[-1], 2)
      prev_close = round(ticker.info.get("previousClose", price), 2)
      change = round(price - prev_close, 2)
      p_change = round((change / prev_close) * 100, 2)
      return {
          "price": f"{price:,.2f}",
          "change": f"{'+' if change >= 0 else ''}{change:,.2f} pts",
          "p_change": f"({'+' if p_change >= 0 else ''}{p_change:.2f}%)",
          "is_positive": change >= 0,
          "timestamp": datetime.datetime.now().strftime(
              "%b %d, %Y, %I:%M:%S %p"
          ),
      }
  except Exception as e:
    print(f"yfinance fetch error: {e}")

  return None


def sync_sensex_from_yahoo():
  """Background loop running on server start to keep data updated."""
  global sensex_data_cache
  while True:
    live_data = fetch_live_sensex()
    if live_data:
      sensex_data_cache = live_data
      print(f"[Sensex Updated]: {live_data['price']}")
    time.sleep(30)  # Refresh every 30 seconds


# Start background syncing thread safely
threading.Thread(target=sync_sensex_from_yahoo, daemon=True).start()


# ==========================================
# 3. ROUTES & API ENDPOINTS
# ==========================================
@app.route("/")
def index():
  return render_template(
      "index.html", sensex=sensex_data_cache
  )  # Adjust template name if needed


@app.route("/api/sensex-live")
def sensex_live():
  return jsonify(sensex_data_cache)


# ==========================================
# 4. RUN APPLICATION
# ==========================================
if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
