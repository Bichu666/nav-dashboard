from datetime import datetime, timedelta, timezone
import json
import os
import random
import re
import shutil
import threading
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import requests
import yfinance as yf
from PIL import Image
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
    default_limits=["10000 per day", "1000 per hour"],
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
ADMIN_MOBILE = "+918078535666"

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
        'rating': 5,
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    },
    {
        'id': 2,
        'username': 'Priya Nair',
        'feedback': 'The historical archive search feature is extremely useful.',
        'rating': 5,
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    },
]

DOWNLOAD_REQUESTS = [
    {
        'id': 1,
        'username': 'Rahul Sharma',
        'filename': 'latest_nav.jpg',
        'type': 'download',
        'status': 'Pending',
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p')
    }
]

PENDING_OTPS = {}


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
      (2026, 1, 14): "Happy Makar Sankranti / Pongal",
      (2026, 1, 26): "Happy Republic Day",
      (2026, 2, 15): "Happy Maha Shivaratri",
      (2026, 3, 4): "Happy Holi",
      (2026, 3, 19): "Happy Ugadi / Gudi Padwa",
      (2026, 3, 26): "Happy Rama Navami",
      (2026, 3, 31): "Happy Mahavir Jayanti",
      (2026, 4, 3): "Happy Good Friday",
      (2026, 4, 14): "Happy Vishu",
      (2026, 5, 1): "Happy Buddha Purnima",
      (2026, 8, 15): "Happy Independence Day",
      (2026, 8, 28): "Happy Raksha Bandhan",
      (2026, 9, 4): "Happy Krishna Janmashtami",
      (2026, 9, 14): "Happy Ganesh Chaturthi",
      (2026, 10, 2): "Happy Mahatma Gandhi Jayanti",
      (2026, 10, 20): "Happy Dussehra",
      (2026, 11, 8): "Happy Diwali",
      (2026, 11, 24): "Happy Guru Nanak Jayanti",
      (2026, 12, 25): "Merry Christmas",

      (2027, 1, 1): "Happy New Year",
      (2027, 1, 15): "Happy Makar Sankranti / Pongal",
      (2027, 1, 26): "Happy Republic Day",
      (2027, 2, 11): "Happy Vasant Panchami",
      (2027, 2, 19): "Happy Shivaji Maharaj Jayanti",
      (2027, 3, 6): "Happy Maha Shivaratri",
      (2027, 3, 10): "Happy Eid al-Fitr",
      (2027, 3, 22): "Happy Holi",
      (2027, 3, 26): "Happy Good Friday",
      (2027, 4, 7): "Happy Ugadi / Gudi Padwa",
      (2027, 4, 14): "Happy Baisakhi / Ambedkar Jayanti",
      (2027, 4, 15): "Happy Rama Navami",
      (2027, 4, 19): "Happy Mahavir Jayanti",
      (2027, 5, 1): "Happy Labour Day",
      (2027, 5, 17): "Happy Eid al-Adha",
      (2027, 5, 20): "Happy Buddha Purnima",
      (2027, 6, 16): "Happy Muharram",
      (2027, 7, 5): "Happy Rathyatra",
      (2027, 8, 15): "Happy Independence Day",
      (2027, 8, 17): "Happy Raksha Bandhan",
      (2027, 8, 25): "Happy Janmashtami",
      (2027, 9, 4): "Happy Ganesh Chaturthi",
      (2027, 9, 12): "Happy Onam",
      (2027, 10, 2): "Happy Mahatma Gandhi Jayanti",
      (2027, 10, 9): "Happy Dussehra",
      (2027, 10, 18): "Happy Karwa Chauth",
      (2027, 10, 29): "Happy Diwali",
      (2027, 10, 31): "Happy Bhaiya Dooj",
      (2027, 11, 4): "Happy Chhath Puja",
      (2027, 11, 14): "Happy Guru Nanak Jayanti",
      (2027, 12, 25): "Merry Christmas",
  }

  recurring_festivals = {
      (1, 1): "Happy New Year",
      (1, 26): "Happy Republic Day",
      (8, 15): "Happy Independence Day",
      (12, 25): "Merry Christmas",
  }

  return festivals_by_date.get((y, m, d), recurring_festivals.get((m, d), None))


def send_email_notification(subject, body):
  sender_email = os.getenv("MAIL_USERNAME", "bijooshpadmakumar522@gmail.com")
  sender_password = os.getenv("MAIL_PASSWORD", "")
  if not sender_password:
    return
  try:
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ADMIN_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
      server.login(sender_email, sender_password)
      server.send_message(msg)
  except Exception as e:
    print(f"Failed to send email: {e}")


def daily_scheduler():
  last_8am_sent = None
  last_10pm_sent = None
  while True:
    try:
      now_utc = datetime.now(timezone.utc)
      ist_now = now_utc + timedelta(hours=5, minutes=30)
      current_date = ist_now.date()
      current_hour = ist_now.hour
      current_minute = ist_now.minute

      if current_hour == 8 and current_minute == 0 and last_8am_sent != current_date:
        body = "Good Morning Bijoosh,\n\nThis is your daily reminder to upload today's latest NAV data on the Admin Portal."
        send_email_notification("Reminder: Upload Today's Latest NAV Data (8:00 AM)", body)
        last_8am_sent = current_date

      if current_hour == 22 and current_minute == 0 and last_10pm_sent != current_date:
        user_summary = "Here is the daily summary of registered users and their details:\n\n"
        for u in REGISTERED_USERS:
          user_summary += f"- Name: {u['name']} | Mobile: {u['mobile']} | Status: {u['status']}\n"
        send_email_notification("Daily User Details Report (10:00 PM)", user_summary)
        last_10pm_sent = current_date
    except Exception as e:
      print(f"Scheduler error: {e}")

    time.sleep(30)


threading.Thread(target=daily_scheduler, daemon=True).start()

CACHE_FILE = 'market_cache.json'

DEFAULT_MARKET_CACHE = {
    'nifty50': {'value': '23,960.60', 'change': '+519.80 pts (+2.22%)', 'is_positive': True},
    'sensex': {'value': '77,301.40', 'change': '+383.55 pts (+0.50%)', 'is_positive': True},
    'nifty500': {'value': '22,769.20', 'change': '+527.80 pts (+2.37%)', 'is_positive': True},
    'trend_data': [
        {'date': '29 Oct', 'nifty50': '22,936.75', 'sensex': '74,151.04', 'nifty500': '21,790.30', 'change': 905.01},
        {'date': '30 Oct', 'nifty50': '23,053.10', 'sensex': '74,459.53', 'nifty500': '21,895.90', 'change': 308.49},
        {'date': '02 Nov', 'nifty50': '23,440.80', 'sensex': '75,692.78', 'nifty500': '22,241.40', 'change': 1233.25},
        {'date': '03 Nov', 'nifty50': '23,810.85', 'sensex': '76,917.85', 'nifty500': '22,520.35', 'change': 1225.07},
        {'date': '04 Nov', 'nifty50': '23,960.60', 'sensex': '77,301.40', 'nifty500': '22,769.20', 'change': 383.55},
    ]
}


def load_market_cache():
  try:
    if os.path.exists(CACHE_FILE):
      with open(CACHE_FILE, 'r') as f:
        return json.load(f)
  except Exception:
    pass
  return DEFAULT_MARKET_CACHE.copy()


def save_market_cache(cache_data):
  try:
    with open(CACHE_FILE, 'w') as f:
      json.dump(cache_data, f)
  except Exception:
    pass


if not os.path.exists(CACHE_FILE):
  save_market_cache(DEFAULT_MARKET_CACHE)


def get_live_market_data():
  cache = load_market_cache()
  now_utc = datetime.now(timezone.utc)
  ist_now = now_utc + timedelta(hours=5, minutes=30)

  is_weekend = ist_now.weekday() >= 5
  is_market_hours = (not is_weekend) and (9 <= ist_now.hour < 16 or (ist_now.hour == 16 and ist_now.minute == 0))

  indices = {
      'nifty50': '^NSEI',
      'sensex': '^BSESN',
      'nifty500': '^CRSLDX'
  }

  result = {}
  for key, ticker in indices.items():
    try:
      t_obj = yf.Ticker(ticker)
      todays_data = t_obj.history(period="2d")
      if not todays_data.empty:
        ltp = float(todays_data['Close'].iloc[-1])
        prev_close = float(todays_data['Close'].iloc[-2]) if len(todays_data) > 1 else ltp
        change = ltp - prev_close
        pct_change = (change / prev_close) * 100 if prev_close else 0
        result[key] = {
            'value': f"{ltp:,.2f}",
            'change': f"{change:+,.2f} pts ({pct_change:+.2f}%)",
            'is_positive': change >= 0
        }
    except Exception as e:
      print(f"yfinance fetch error for {key}: {e}")

    if key not in result:
      cached_item = cache.get(key, {})
      result[key] = {
          'value': cached_item.get('value', '0.00'),
          'change': cached_item.get('change', '+0.00 pts (0.00%)'),
          'is_positive': cached_item.get('is_positive', True)
      }

  trend_data = []
  try:
    sensex_hist = yf.Ticker('^BSESN').history(period="6d")
    if not sensex_hist.empty and len(sensex_hist) >= 2:
      sensex_hist = sensex_hist.tail(5)
      prev_val = None
      for idx, row in sensex_hist.iterrows():
        dt_str = idx.strftime('%d %b')
        close_val = float(row['Close'])
        if prev_val is not None:
          chg = round(close_val - prev_val, 2)
        else:
          chg = 0.0
        prev_val = close_val
        trend_data.append({
            'date': dt_str,
            'sensex': f"{close_val:,.2f}",
            'change': chg
        })
  except Exception as e:
    print(f"yfinance trend fetch error: {e}")

  if not trend_data:
    trend_data = cache.get('trend_data', [])

  if not is_market_hours:
    time_label = f"CLOSED | As on 04:00 PM | {ist_now.strftime('%d %b %Y')}"
  else:
    time_label = f"Live as of: {ist_now.strftime('%b %d, %Y, %I:%M:%S %p')}"

  return {
      'nifty50': result['nifty50'],
      'sensex': result['sensex'],
      'nifty500': result['nifty500'],
      'time_label': time_label,
      'is_market_open': is_market_hours
  }, trend_data


@app.route('/api/market-live')
@limiter.exempt
def market_live():
  market_info, _ = get_live_market_data()
  return