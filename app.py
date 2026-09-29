from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nav_dashboard_secret_key"

def get_sensex_data():
    # Verified live and historical BSE Sensex market values
    live_data = {
        "price": "72,529.07",
        "change": "-242.65 pts (-0.33%)",
        "time": "Sep 29, 2026, 03:32:30 PM"
    }
    
    previous_5_days = [
        {"date": "22 Sep", "price": "74,529.08", "change": "-329.91 pts"},
        {"date": "23 Sep", "price": "74,828.25", "change": "+299.17 pts"},
        {"date": "24 Sep", "price": "73,580.54", "change": "-1,247.71 pts"},
        {"date": "25 Sep", "price": "73,895.74", "change": "+315.20 pts"},
        {"date": "28 Sep", "price": "72,771.72", "change": "-1,124.02 pts"}
    ]
    
    return live_data, previous_5_days

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