import datetime
import json
import os
from breeze_connect import BreezeConnect

# 1. Initialize the SDK with your App Key
breeze = BreezeConnect(api_key="40d6o1T87b806978867rY54E59#98179")

def live():
    print("\n==================================================")
    print(" Running Live Sensex Cache Updater (Breeze API)...")
    print("==================================================")

    # Step A: Authenticate Breeze Session (Using your latest session token)
    session_token = os.getenv("BREEZE_SESSION_TOKEN", "57397128")
    breeze_authenticated = False
    
    try:
        breeze.generate_session(
            api_secret="786eM698GP2!x0592I7m4w3856452u1V",
            session_token=session_token
        )
        print(" SUCCESS: Connected and Authenticated with Breeze API!")
        breeze_authenticated = True
    except Exception as e:
        print(" WARNING: Breeze API Session failed:", str(e))

    sensex_data = None
    data_source = "Breeze API"

    # Step B: Fetch via Breeze API using correct BSESEN code
    if breeze_authenticated:
        try:
            today_date = datetime.datetime.now().strftime("%Y-%m-%dT00:00:00.000Z")
            response = breeze.get_historical_data_v2(
                interval="1minute",
                from_date=today_date,
                to_date=today_date,
                stock_code="BSESEN",
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

    # Step C: Save data safely into sensex_cache.json
    if sensex_data and sensex_data.get("live_price", 0) > 0:
        cache_path = "sensex_cache.json"
        with open(cache_path, "w") as f:
            json.dump(sensex_data, f, indent=4)
        print(f"\n Successfully updated '{cache_path}' using {data_source}!")
        print(" Data:", sensex_data)
    else:
        print("\n Error: Could not retrieve market data from Breeze API.")
    print("==================================================\n")

if __name__ == "__main__":
    live()