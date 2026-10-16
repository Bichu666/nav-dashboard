from datetime import datetime, timedelta, timezone
import json
import os
import re
import shutil
import threading
import time
import pandas as pd
import requests
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.secret_key = 'nav_updates_secret_key'

app.permanent_session_lifetime = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL) if DATABASE_URL else None

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ARCHIVE_FOLDER = 'archive_nav'
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

ADMIN_ACTIVITY = {'last_active': datetime.now()}
ADMIN_SETTINGS = {'auto_approval_enabled': True}
ADMIN_EMAIL = "bijooshpadmakumar522@gmail.com"

REGISTERED_USERS = [
    {
        'id': 1,
        'name': 'Rahul Sharma',
        'mobile': '+91 9876543210',
        'status': 'Pending',
        'registered_at': datetime.now() - timedelta(minutes=3),
        'approved_at': None,
    },
    {
        'id': 2,
        'name': 'Priya Nair',
        'mobile': '+91 9876522888',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(days=5),
        'approved_at': datetime.now().isoformat(),
    },
    {
        'id': 3,
        'name': 'biju',
        'mobile': '+917034788666',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(days=10),
        'approved_at': datetime.now().isoformat(),
    },
]

USER_FEEDBACKS = [
    {
        'id': 1,
        'username': 'Rahul Sharma',
        'feedback': 'Great portal! Very intuitive and fast NAV updates.',
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    },
    {
        'id': 2,
        'username': 'Priya Nair',
        'feedback': 'The historical archive search feature is extremely useful.',
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    },
]

def check_user_validity(user):
  if not ADMIN_SETTINGS.get('auto_approval_enabled', True):
    return
  now = datetime.now()
  if user['status'] == 'Pending':
    reg_time = user.get('registered_at', now)
    if now - reg_time > timedelta(minutes=5):
      user['status'] = 'Approved'
      user['approved_at'] = now.isoformat()

  if user['status'] == 'Approved' and user.get('approved_at'):
    approved_date = datetime.fromisoformat(user['approved_at'])
    if now - approved_date > timedelta(days=30):
      user['status'] = 'Pending'
      user['approved_at'] = None
      user['registered_at'] = now

def get_festival_greeting():
  now_utc = datetime.now(timezone.utc)
  ist_now = now_utc + timedelta(hours=5, minutes=30)
  m = ist_now.month
  d = ist_now.day
  y = ist_now.year

  festivals_by_date = {
      (2026, 1, 1): "Happy New Year",
      (2026, 1, 26): "Happy Republic Day",
      (2026, 8, 15): "Happy Independence Day",
      (2026, 9, 4): "Happy Onam",
      (2026, 11, 8): "Happy Diwali",
      (2026, 12, 25): "Merry Christmas",
  }
  return festivals_by_date.get((y, m, d), None)

CACHE_FILE = 'sensex_cache.json'

def sync_sensex_from_yahoo():
  while True:
    try:
      url = "https://query1.finance.yahoo.com/v8/finance/chart/^BSESN?range=10d&interval=1d"
      headers = {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      }
      response = requests.get(url, headers=headers, timeout=10)
      if response.status_code == 200:
        data = response.json()
        result = data['chart']['result'][0]
        meta = result['meta']
        
        current_val = float(meta['regularMarketPrice'])
        prev_close = float(meta['chartPreviousClose'])

        # Calculate exact change against previous close
        pts_change = round(current_val - prev_close, 2)
        pct_change = round((pts_change / prev_close) * 100, 2)

        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]['close']

        valid_entries = []
        for i in range(len(timestamps)):
          if quotes[i] is not None:
            dt = datetime.fromtimestamp(timestamps[i])
            valid_entries.append({
                'date': dt.strftime('%d %b'),
                'close': float(quotes[i])
            })

        trend_list = []
        for idx in range(len(valid_entries)):
          curr = valid_entries[idx]
          if idx > 0:
            prev_c = valid_entries[idx - 1]['close']
            chg = round(curr['close'] - prev_c, 2)
          else:
            chg = 0.0

          trend_list.append({
              'date': curr['date'],
              'value': f"{curr['close']:,.2f}",
              'change': chg
          })

        cache_data = {
            'value': round(current_val, 2),
            'base_change_pts': round(pts_change, 2),
            'pct_change': round(pct_change, 2),
            'is_positive': pts_change >= 0,
            'last_close_time': datetime.now().strftime('%I:%M:%S %p GMT+5:30'),
            'trend_data': trend_list[-5:]
        }

        with open(CACHE_FILE, 'w') as f:
          json.dump(cache_data, f)
    except Exception as e:
      print(f"Sensex sync background error: {e}")

    time.sleep(15)

threading.Thread(target=sync_sensex_from_yahoo, daemon=True).start()

def get_sensex_data():
  if os.path.exists(CACHE_FILE):
    try:
      with open(CACHE_FILE, 'r') as f:
        cache = json.load(f)
        now_utc = datetime.now(timezone.utc)
        ist_now = now_utc + timedelta(hours=5, minutes=30)
        
        return {
            'value': f"{cache['value']:,.2f}",
            'change': f"{cache['base_change_pts']:+,.2f} pts ({cache['pct_change']:+.2f}%)",
            'is_positive': cache['is_positive'],
            'time_label': f"Live as of: {ist_now.strftime('%b %d, %Y, %I:%M:%S %p')}",
            'is_market_open': True
        }, cache.get('trend_data', [])
    except Exception:
      pass

  return {
      'value': '74,595.96',
      'change': '+280.35 pts (+0.38%)',
      'is_positive': True,
      'time_label': 'Live Market',
      'is_market_open': True
  }, []

@app.route('/api/sensex-live')
def sensex_live():
  sensex_info, _ = get_sensex_data()
  return jsonify(sensex_info)

@app.route('/user-dashboard')
def user_dashboard():
  mobile = session.get('mobile', '')
  sensex_info, sensex_trend_data = get_sensex_data()
  admin_online = (datetime.now() - ADMIN_ACTIVITY['last_active']) < timedelta(minutes=5)
  festival_greeting = get_festival_greeting()

  return render_template(
      'user_dashboard.html',
      username=session.get('username', 'Client'),
      mobile=mobile,
      sensex=sensex_info,
      sensex_trend=sensex_trend_data,
      admin_online=admin_online,
      festival_greeting=festival_greeting,
  )

@app.route('/admin-dashboard')
def admin_dashboard():
  sensex_info, sensex_trend_data = get_sensex_data()
  return render_template(
      'admin_dashboard.html',
      sensex=sensex_info,
      sensex_trend=sensex_trend_data,
      users=REGISTERED_USERS,
      feedbacks=USER_FEEDBACKS,
      auto_approval_enabled=ADMIN_SETTINGS['auto_approval_enabled'],
      current_time=datetime.now().strftime('%b %d, %Y, %I:%M:%S %p'),
  )

if __name__ == '__main__':
  app.run(debug=True)