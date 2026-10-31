from datetime import datetime, timedelta, timezone
import json
import os
import random
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

DOWNLOAD_REQUESTS = []


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

CACHE_FILE = 'sensex_cache.json'

DEFAULT_SENSEX_CACHE = {
    'value': 74729.27,
    'base_change_pts': 413.66,
    'pct_change': 0.56,
    'is_positive': True,
    'last_close_time': '04:00:00 PM IST',
    'trend_data': [
        {'date': '12 Oct', 'value': '71,924.68', 'change': -846.64},
        {'date': '13 Oct', 'value': '73,033.78', 'change': 1082.05},
        {'date': '14 Oct', 'value': '72,781.89', 'change': -267.87},
        {'date': '15 Oct', 'value': '74,315.61', 'change': 1533.72},
        {'date': '16 Oct', 'value': '74,729.27', 'change': 413.66},
    ]
}


def load_sensex_cache():
  try:
    if os.path.exists(CACHE_FILE):
      with open(CACHE_FILE, 'r') as f:
        return json.load(f)
  except Exception:
    pass
  return DEFAULT_SENSEX_CACHE.copy()


def save_sensex_cache(cache_data):
  try:
    with open(CACHE_FILE, 'w') as f:
      json.dump(cache_data, f)
  except Exception:
    pass


if not os.path.exists(CACHE_FILE):
  save_sensex_cache(DEFAULT_SENSEX_CACHE)


def get_live_sensex_from_public_api():
  cache = load_sensex_cache()
  default_val = float(str(cache.get('value', 74729.27)).replace(',', ''))
  
  try:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/^BSESN?interval=1m"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, timeout=5)
    
    if response.status_code == 200:
      res_json = response.json()
      meta = res_json['chart']['result'][0]['meta']
      ltp = float(meta.get('regularMarketPrice', 0))
      prev_close = float(meta.get('chartPreviousClose', ltp))
      
      if ltp > 0:
        change = ltp - prev_close
        pct_change = (change / prev_close) * 100 if prev_close else 0
        
        now_utc = datetime.now(timezone.utc)
        ist_now = now_utc + timedelta(hours=5, minutes=30)
        
        return {
            'value': f"{ltp:,.2f}",
            'change': f"{change:+,.2f} pts ({pct_change:+.2f}%)",
            'is_positive': change >= 0,
            'time_label': f"Live as of: {ist_now.strftime('%b %d, %Y, %I:%M:%S %p')}",
            'is_market_open': True
        }
  except Exception as e:
    print(f"Live Market Fetch Error: {e}")

  now_utc = datetime.now(timezone.utc)
  ist_now = now_utc + timedelta(hours=5, minutes=30)
  pts_change = float(cache.get('base_change_pts', 413.66))
  pct_change = float(cache.get('pct_change', 0.56))
  
  return {
      'value': f'{default_val:,.2f}',
      'change': f'{pts_change:+,.2f} pts ({pct_change:+.2f}%)',
      'is_positive': pts_change >= 0,
      'time_label': f"At close: 04:00:00 PM IST",
      'is_market_open': False
  }


def get_sensex_data():
  cache = load_sensex_cache()
  live_info = get_live_sensex_from_public_api()
  return live_info, cache.get('trend_data', [])


@app.route('/api/sensex-live')
@limiter.exempt
def sensex_live():
  sensex_info, _ = get_sensex_data()
  return jsonify(sensex_info)


def format_pct(val):
  try:
    return round(float(val) * 100, 2)
  except:
    return val


def parse_fund_excel_from_db(table_name):
  fund_list = []
  if not engine:
    return fund_list
  try:
    df = pd.read_sql(f'SELECT * FROM {table_name}', engine)
    if not df.empty:
      df = df.dropna(subset=[df.columns[0]])
      for _, row in df.iterrows():
        val = str(row.iloc[0]).strip()
        if val and val.lower() not in ['nan', 'funds']:
          fund_list.append({
              'fund': val,
              'inception': str(row.iloc[1]) if len(row) > 1 else '',
              'benchmark': str(row.iloc[2]) if len(row) > 2 else '',
              'since': format_pct(row.iloc[3]) if len(row) > 3 else '0',
              'm1': format_pct(row.iloc[4]) if len(row) > 4 else '0',
              'm6': format_pct(row.iloc[5]) if len(row) > 5 else '0',
              'y1': format_pct(row.iloc[6]) if len(row) > 6 else '0',
              'y2': format_pct(row.iloc[7]) if len(row) > 7 else '0',
              'y3': format_pct(row.iloc[8]) if len(row) > 8 else '0',
              'y4':