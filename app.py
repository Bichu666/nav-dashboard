import datetime
import threading
import time
import requests
import yfinance as yf


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
