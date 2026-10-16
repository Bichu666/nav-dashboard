import datetime
import json
import os
import yfinance as yf
from breeze_connect import BreezeConnect

# 1. Initialize the SDK with your App Key
breeze = BreezeConnect(api_key="40d6o1T87b806978867rY54E59#98179")

def live():
    print("\n==================================================")
    print(" Running Live Sensex Cache Updater...")
    print("==================================================")

    # Step A: Authenticate Breeze Session
    breeze_authenticated = False
    try:
        breeze.generate_session(
            api_secret="786eM698GP2!x0592I7m4w3856452u1V",
            session_token="57378956"
        )
        print(" SUCCESS: Connected and Authenticated with Breeze API!")
        breeze_authenticated = True
    except Exception as e:
        print(" WARNING: Breeze API Session failed:", str(e))

    sensex_data = None
    data_source = "Breeze API"

    # Step B: Try Breeze API
    if breeze_authenticated:
        try:
            today_date = datetime.datetime.now().strftime("%Y-%m-%dT00:00:00.000Z")
            response = breeze.get_historical_data_v2(
                interval="1minute",
                from_date=today_date,
                to_date=today_date,
                stock_code="BSESN",
                exchange_code="BSE",
                product_type="cash"
            )
            if response and response.get('Status') == 200 and response.get('Success'):
                candles = response.get('Success')
                if candles:
                    latest = candles[-1]
                    sensex_data = {
                        "live_price": float(latest.get('close', 0)),
                        "change_pts": 0.0,
                        "change_pct": 0.0,
                        "timestamp": datetime.datetime.now().strftime("%I:%M:%S %p IST")
                    }
        except Exception as err:
            print(" Breeze API Fetch Error:", err)

    # Step C: Fallback to Yahoo Finance Feed (if Breeze didn't return candle values)
    if not sensex_data:
        data_source = "Yahoo Finance (BSE Sensex Feed)"
        try:
            ticker = yf.Ticker("^BSESN")
            info = ticker.history(period="6d", interval="1d")
            
            if not info.empty:
                latest_close = float(info['Close'].iloc[-1])
                prev_close = float(info['Close'].iloc[-2]) if len(info) > 1 else latest_close
                change = latest_close - prev_close
                pct_change = (change / prev_close) * 100

                # Build last 5 days trend list for your dashboard
                historical_trend = []
                for idx, row in info.tail(5).iterrows():
                    historical_trend.append({
                        "date": idx.strftime("%d %b"),
                        "close": round(float(row['Close']), 2),
                        "change": round(float(row['Close'] - row['Open']), 2)
                    })

                sensex_data = {
                    "live_price": round(latest_close, 2),
                    "change_pts": round(change, 2),
                    "change_pct": round(pct_change, 2),
                    "timestamp": datetime.datetime.now().strftime("%I:%M:%S %p IST"),
                    "market_status": "At close",
                    "historical_5days": historical_trend
                }
        except Exception as yf_err:
            print(" Fallback Fetch Error:", yf_err)

    # Step D: Save data safely into sensex_cache.json (Your NAV files are completely untouched)
    if sensex_data:
        cache_path = "sensex_cache.json"
        with open(cache_path, "w") as f:
            json.dump(sensex_data, f, indent=4)
        print(f"\n Successfully updated '{cache_path}' using {data_source}!")
        print(" Data:", sensex_data)
    else:
        print("\n Error: Could not retrieve market data from any source.")
    print("==================================================\n")

if __name__ == "__main__":
    live()