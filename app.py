from flask import Flask, render_template, request, redirect, url_for, flash
import yfinance as yf
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nav_dashboard_secret_key"

def get_sensex_data():
    try:
        # Safely fetching BSE Sensex (^BSESN) data via yfinance
        sensex = yf.Ticker("^BSESN")
        df = sensex.history(period="10d")
        
        if df.empty:
            raise ValueError("Empty dataframe returned")
            
        latest_close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        change = latest_close - prev_close
        pct_change = (change / prev_close) * 100
        
        live_data = {
            "price": f"{latest_close:,.2f}",
            "change": f"{'+' if change >= 0 else ''}{change:,.2f} pts ({'+' if pct_change >= 0 else ''}{pct_change:.2f}%)",
            "time": datetime.now().strftime("%b %d, %Y, %I:%M:%S %p")
        }
        
        # Last 5 trading sessions for the trend panel
        trend_df = df.tail(5)
        previous_5_days = []
        for i in range(len(trend_df)):
            row = trend_df.iloc[i]
            date_str = trend_df.index[i].strftime("%d %b")
            price_str = f"{row['Close']:,.2f}"
            
            if i > 0:
                diff = row['Close'] - trend_df['Close'].iloc[i-1]
                diff_str = f"{'+' if diff >= 0 else ''}{diff:,.2f} pts"
            else:
                diff_str = "0.00 pts"
                
            previous_5_days.append({
                "date": date_str,
                "price": price_str,
                "change": diff_str
            })
            
        return live_data, previous_5_days
    except Exception as e:
        print(f"Live data fetch error: {e}")
        # Fallback dictionary matching your precise layout values
        fallback_live = {
            "price": "72,529.07",
            "change": "-242.65 pts (-0.33%)",
            "time": datetime.now().strftime("%b %d, %Y, %I:%M:%S %p")
        }
        fallback_trend = [
            {"date": "22 Sep", "price": "74,529.08", "change": "-329.91 pts"},
            {"date": "23 Sep", "price": "74,828.25", "change": "+299.17 pts"},
            {"date": "24 Sep", "price": "73,580.54", "change": "-1,247.71 pts"},
            {"date": "25 Sep", "price": "73,895.74", "change": "+315.20 pts"},
            {"date": "28 Sep", "price": "72,771.72", "change": "-1,124.02 pts"}
        ]
        return fallback_live, fallback_trend

@app.route('/admin-dashboard')
def admin_dashboard():
    live_data, previous_5_days = get_sensex_data()
    users = [
        {"id": 1, "name": "Rahul Sharma (ID: 1)", "mobile": "+91 9876543210", "status": "Pending"},
        {"id": 2, "name": "Priya Nair (ID: 2)", "mobile": "+91 9876522888", "status": "Approved"},
        {"id": 3, "name": "biju (ID: 3)", "mobile": "+91 9703478866", "status": "Approved"}
    ]
    return render_template('admin-dashboard.html', live_data=live_data, previous_5_days=previous_5_days, users=users)

@app.route('/user-dashboard')
def user_dashboard():
    live_data, previous_5_days = get_sensex_data()
    return render_template('user-dashboard.html', live_data=live_data, previous_5_days=previous_5_days)

@app.route('/')
def home():
    return redirect(url_for('user_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)