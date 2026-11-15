import base64
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import hmac
import json
import os
import random
import re
import shutil
import smtplib
import threading
import time
<<<<<<< HEAD
from urllib.parse import quote, unquote

=======
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import requests
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)
from flask import (
    Flask,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
<<<<<<< HEAD
=======
import smtplib
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pandas as pd
from PIL import Image
import requests
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename
import yfinance as yf

app = Flask(__name__)
app.secret_key = 'nav_updates_secret_key'

app.permanent_session_lifetime = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

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

PORTFOLIO_STORE_FILE = os.path.join(UPLOAD_FOLDER, 'fund_portfolios_store.json')

ADMIN_ACTIVITY = {'last_active': datetime.now()}
ADMIN_SETTINGS = {'auto_approval_enabled': True}
ADMIN_EMAIL = "bijooshpadmakumar522@gmail.com"

# Green-API Configuration and Admin WhatsApp Target
GREEN_API_ID_INSTANCE = "710722793507"
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN", "92579905afbb4198a8e249f7092382fe9f5de4df4d0242d09c")
ADMIN_WHATSAPP_RECIPIENT = os.getenv("GREEN_API_RECIPIENT", os.getenv("ADMIN_WHATSAPP_NUMBER", "120363413370592164@g.us"))

AUTO_LOGIN_COOKIE_NAME = 'nav_auto_login'
AUTO_LOGIN_TOKENS = {}


def send_whatsapp_alert(message_text):
    def _send():
        url = f"https://7107.api.greenapi.com/waInstance{GREEN_API_ID_INSTANCE}/sendMessage/{GREEN_API_TOKEN}"
        payload = {"chatId": ADMIN_WHATSAPP_RECIPIENT, "message": message_text}
        headers = {'Content-Type': 'application/json'}
        try:
            requests.post(url, json=payload, headers=headers, timeout=10)
        except Exception as e:
            print(f"Green-API Exception Error: {e}")

    threading.Thread(target=_send, daemon=True).start()


REGISTERED_USERS = [
    {
        'id': 1,
        'name': 'Rahul Sharma',
        'mobile': '+91 9876543210',
        'status': 'Pending',
        'registered_at': datetime.now() - timedelta(minutes=3),
        'approved_at': None,
        'session_started_at': datetime.now() - timedelta(minutes=3),
        'last_login': 'Nov 06, 2026, 09:45 PM',
        'last_active': datetime.now() - timedelta(minutes=2),
    },
    {
        'id': 2,
        'name': 'Priya Nair',
        'mobile': '+91 9876522888',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(days=5),
        'approved_at': (datetime.now() - timedelta(days=5)).isoformat(),
        'session_started_at': datetime.now() - timedelta(days=5),
        'last_login': 'Nov 06, 2026, 08:30 PM',
        'last_active': datetime.now() - timedelta(minutes=1),
    },
    {
        'id': 3,
        'name': 'biju',
        'mobile': '+917034788666',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(days=10),
        'approved_at': (datetime.now() - timedelta(days=10)).isoformat(),
        'session_started_at': datetime.now() - timedelta(days=10),
        'last_login': 'Nov 06, 2026, 10:00 PM',
        'last_active': datetime.now(),
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

<<<<<<< HEAD
CHAT_MESSAGES = [
    {
        'id': 1,
        'username': 'biju',
        'recipient': 'Admin',
        'message': 'Hello Admin, checking connection.',
        'timestamp': 'Nov 06, 2026, 10:00 PM',
        'sender': 'user'
    }
]

PENDING_OTPS = {}


def _sign_auto_token(payload_str):
    sig = hmac.new(
        app.secret_key.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{payload_str}.{sig}"


def _verify_auto_token(token_str):
    if not token_str or '.' not in token_str:
        return None
    payload_str, sig = token_str.rsplit('.', 1)
    expected = hmac.new(
        app.secret_key.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return payload_str


def issue_auto_login_cookie(response, username, mobile, is_admin=False):
    raw_nonce = f"{username}|{mobile}|{int(is_admin)}|{datetime.now(timezone.utc).timestamp()}|{random.randint(100000, 999999)}"
    signed_token = _sign_auto_token(raw_nonce)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    AUTO_LOGIN_TOKENS[signed_token] = {
        'username': username,
        'mobile': mobile,
        'is_admin': is_admin,
        'expires_at': expires_at,
        'revoked': False,
    }
    response.set_cookie(
        AUTO_LOGIN_COOKIE_NAME,
        signed_token,
        max_age=30 * 24 * 60 * 60,
        expires=expires_at,
        httponly=True,
        samesite='Lax',
        secure=request.is_secure,
    )
    return response


def revoke_auto_login_cookie(response):
    token = request.cookies.get(AUTO_LOGIN_COOKIE_NAME)
    if token and token in AUTO_LOGIN_TOKENS:
        AUTO_LOGIN_TOKENS[token]['revoked'] = True
    response.delete_cookie(AUTO_LOGIN_COOKIE_NAME, httponly=True, samesite='Lax')
    return response


def validate_and_restore_auto_session():
    if 'username' in session or session.get('is_admin'):
        return True
    token = request.cookies.get(AUTO_LOGIN_COOKIE_NAME)
    if not token or not _verify_auto_token(token):
        return False
    entry = AUTO_LOGIN_TOKENS.get(token)
    if not entry or entry.get('revoked'):
        return False
    if datetime.now(timezone.utc) > entry['expires_at']:
        entry['revoked'] = True
        return False

    if entry.get('is_admin'):
        session.permanent = True
        session['is_admin'] = True
        ADMIN_ACTIVITY['last_active'] = datetime.now()
        return True

    mobile = entry.get('mobile', '')
    user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
    if not user_record:
        return False
    check_user_validity(user_record)
    if user_record['status'] != 'Approved':
        return False

    session.permanent = True
    session['username'] = user_record['name']
    session['mobile'] = user_record['mobile']
    user_record['last_active'] = datetime.now()
    return True
=======
PENDING_OTPS = {}
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


def check_user_validity(user):
    if not ADMIN_SETTINGS.get('auto_approval_enabled', True):
        return
    now = datetime.now()
    if user['status'] == 'Pending':
        reg_time = user.get('registered_at', now)
        if now - reg_time > timedelta(minutes=2):
            user['status'] = 'Approved'
            user['approved_at'] = now.isoformat()
            user['session_started_at'] = now


def get_remaining_validity_days(user):
    if not user:
        return 30
    start_raw = user.get('session_started_at') or user.get('approved_at') or user.get('registered_at')
    if isinstance(start_raw, str):
        try:
            start_dt = datetime.fromisoformat(start_raw)
        except Exception:
            start_dt = datetime.now()
    elif isinstance(start_raw, datetime):
        start_dt = start_raw
    else:
        start_dt = datetime.now()

    elapsed = datetime.now() - start_dt
    remaining = 30 - elapsed.days
    if elapsed.total_seconds() < 0:
        remaining = 30
    return max(0, min(30, remaining))


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
    except Exception:
        pass


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
        except Exception:
            pass
        time.sleep(30)


threading.Thread(target=daily_scheduler, daemon=True).start()

CACHE_FILE = 'market_cache.json'
<<<<<<< HEAD
DEFAULT_MARKET_CACHE = {
    'nifty50': {'value': '24,350.20', 'change': '+145.20 pts (+0.60%)', 'is_positive': True},
    'sensex': {'value': '81,911.01', 'change': '+31.61 pts (+0.04%)', 'is_positive': True},
    'nifty500': {'value': '23,120.40', 'change': '+132.10 pts (+0.57%)', 'is_positive': True},
    'trend_data': [
        {'date': '06 Nov', 'sensex': '79,413.66', 'change': -1614.36},
        {'date': '09 Nov', 'sensex': '81,106.65', 'change': 1692.99},
        {'date': '11 Nov', 'sensex': '81,879.40', 'change': 772.75},
        {'date': '12 Nov', 'sensex': '82,150.57', 'change': 271.17},
        {'date': '13 Nov', 'sensex': '81,911.01', 'change': 31.61},
=======

DEFAULT_MARKET_CACHE = {
    'nifty50': {'value': '23,053.10', 'change': '+116.35 pts (+0.51%)', 'is_positive': True},
    'sensex': {'value': '74,459.53', 'change': '+308.49 pts (+0.42%)', 'is_positive': True},
    'nifty500': {'value': '21,895.90', 'change': '-45.60 pts (-0.21%)', 'is_positive': False},
    'trend_data': [
        {'date': '26 Oct', 'nifty50': '22,850.10', 'sensex': '73,924.68', 'nifty500': '21,650.00', 'change': -120.50},
        {'date': '27 Oct', 'nifty50': '22,940.25', 'sensex': '74,103.78', 'nifty500': '21,740.10', 'change': 180.25},
        {'date': '28 Oct', 'nifty50': '22,890.00', 'sensex': '73,981.89', 'nifty500': '21,700.50', 'change': -50.25},
        {'date': '29 Oct', 'nifty50': '22,936.75', 'sensex': '74,151.04', 'nifty500': '21,790.30', 'change': 210.15},
        {'date': '30 Oct', 'nifty50': '23,053.10', 'sensex': '74,459.53', 'nifty500': '21,895.90', 'change': 308.49},
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)
    ]
}


def load_market_cache():
<<<<<<< HEAD
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_MARKET_CACHE.copy()


def get_live_market_data():
    cache = load_market_cache()
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    is_weekend = ist_now.weekday() >= 5
    is_market_hours = (not is_weekend) and (9 <= ist_now.hour < 16 or (ist_now.hour == 16 and ist_now.minute == 0))
=======
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
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)

    result = {}
    indices = {'nifty50': '^NSEI', 'sensex': '^BSESN', 'nifty500': '^CRSLDX'}

<<<<<<< HEAD
    for key, ticker in indices.items():
        cached_item = cache.get(key, {})
        result[key] = {
            'value': cached_item.get('value', '0.00'),
            'change': cached_item.get('change', '+0.00 pts (0.00%)'),
            'is_positive': cached_item.get('is_positive', True)
        }

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
=======
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
  headers = {'User-Agent': 'Mozilla/5.0'}

  for key, ticker in indices.items():
    try:
      url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m"
      response = requests.get(url, headers=headers, timeout=4)
      if response.status_code == 200:
        res_json = response.json()
        meta = res_json['chart']['result'][0]['meta']
        ltp = float(meta.get('regularMarketPrice', 0))
        prev_close = float(meta.get('chartPreviousClose', ltp))
        if ltp > 0:
          change = ltp - prev_close
          pct_change = (change / prev_close) * 100 if prev_close else 0
          result[key] = {
              'value': f"{ltp:,.2f}",
              'change': f"{change:+,.2f} pts ({pct_change:+.2f}%)",
              'is_positive': change >= 0
          }
    except Exception:
      pass

    if key not in result:
      cached_item = cache.get(key, {})
      result[key] = {
          'value': cached_item.get('value', '0.00'),
          'change': cached_item.get('change', '+0.00 pts (0.00%)'),
          'is_positive': cached_item.get('is_positive', True)
      }

  if not is_market_hours:
    time_label = f"CLOSED | As on 04:00 PM | 30 Oct 2026"
  else:
    time_label = f"Live as of: {ist_now.strftime('%b %d, %Y, %I:%M:%S %p')}"

  return {
      'nifty50': result['nifty50'],
      'sensex': result['sensex'],
      'nifty500': result['nifty500'],
      'time_label': time_label,
      'is_market_open': is_market_hours
  }, cache.get('trend_data', [])
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/api/market-live')
@limiter.exempt
def market_live():
<<<<<<< HEAD
    market_info, _ = get_live_market_data()
    return jsonify(market_info)


@app.route('/api/market-sync', methods=['POST'])
@limiter.exempt
def market_sync():
    validate_and_restore_auto_session()
    if 'username' not in session and not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    data = request.get_json() or {}
    if not all(k in data for k in ('nifty50', 'sensex', 'nifty500')):
        return jsonify({'success': False, 'message': 'Invalid market payload'}), 400

    cache = load_market_cache()
    for key in ('nifty50', 'sensex', 'nifty500'):
        if isinstance(data.get(key), dict):
            cache[key] = {
                'value': str(data[key].get('value', cache.get(key, {}).get('value', '0.00'))),
                'change': str(data[key].get('change', cache.get(key, {}).get('change', '+0.00 pts (0.00%)'))),
                'is_positive': bool(data[key].get('is_positive', True)),
            }
    if isinstance(data.get('trend_data'), list) and data['trend_data']:
        cache['trend_data'] = data['trend_data']

    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception:
        pass

    return jsonify({'success': True})


@app.route('/api/heartbeat', methods=['POST'])
@limiter.exempt
def heartbeat():
    validate_and_restore_auto_session()
    if session.get('is_admin'):
        ADMIN_ACTIVITY['last_active'] = datetime.now()
    elif 'username' in session:
        mobile = session.get('mobile', '')
        user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
        if user_record:
            user_record['last_active'] = datetime.now()
    return jsonify({'success': True})


@app.route('/api/messages', methods=['GET'])
@app.route('/api/get-messages', methods=['GET'])
@app.route('/api/messages/get', methods=['GET'])
def get_messages():
    validate_and_restore_auto_session()
    if 'username' not in session and not session.get('is_admin'):
        return jsonify({'success': False, 'messages': []})

    if session.get('is_admin'):
        user_filter = request.args.get('user', '')
        if not user_filter or user_filter == 'all':
            return jsonify({'success': True, 'messages': CHAT_MESSAGES})
        filtered = [m for m in CHAT_MESSAGES if m['username'] == user_filter or m.get('recipient') == user_filter]
        return jsonify({'success': True, 'messages': filtered})
    else:
        current_username = session.get('username')
        filtered = [m for m in CHAT_MESSAGES if m['username'] == current_username or m.get('recipient') == current_username]
        return jsonify({'success': True, 'messages': filtered})


@app.route('/api/send-message', methods=['POST'])
def send_message():
    validate_and_restore_auto_session()
    if 'username' not in session and not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'})

    data = request.get_json() or {}
    msg_text = data.get('message', '').strip()
    if not msg_text:
        return jsonify({'success': False, 'message': 'Empty message'})

    now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    timestamp_str = now_ist.strftime('%b %d, %Y, %I:%M %p')

    is_admin_user = session.get('is_admin', False)
    username = 'Admin Bijoosh' if is_admin_user else session.get('username', 'Client')
    sender_type = 'admin' if is_admin_user else 'user'
    recipient = data.get('recipient', 'Admin') if is_admin_user else 'Admin'

    new_msg = {
        'id': len(CHAT_MESSAGES) + 1,
        'username': username,
        'recipient': recipient,
        'message': msg_text,
        'timestamp': timestamp_str,
        'sender': sender_type
    }
    CHAT_MESSAGES.append(new_msg)

    if is_admin_user:
        send_whatsapp_alert(f"💬 *Admin Reply to {recipient}*\n\n*Message:* {msg_text}")
    else:
        send_whatsapp_alert(f"💬 *New Chat Message*\n\n*User:* {username}\n*Message:* {msg_text}")

    return jsonify({'success': True, 'message': 'Message sent successfully.'})
=======
  market_info, _ = get_live_market_data()
  return jsonify(market_info)
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


def format_pct(val):
    try:
        return round(float(val) * 100, 2)
    except Exception:
        return val


def load_portfolio_store():
    try:
        if os.path.exists(PORTFOLIO_STORE_FILE):
            with open(PORTFOLIO_STORE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {'equity': {}, 'balancer': {}, 'debt': {}}


def save_portfolio_store(store):
    try:
        with open(PORTFOLIO_STORE_FILE, 'w', encoding='utf-8') as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Portfolio store save error: {e}")


def _parse_single_fund_sheet(df):
    if df is None or df.empty:
        return None

    # Cell A1 (Row 0, Col 0) contains the exact full fund name
    fund_name_raw = df.iloc[0, 0] if df.shape[1] > 0 else None
    fund_name = str(fund_name_raw).strip() if pd.notna(fund_name_raw) else ''
    if not fund_name or fund_name.lower() in ['nan', 'none']:
        return None

    sectors = []
    holdings = []
    mode = None  # 'sectors' | 'holdings'

    for r_idx in range(1, len(df)):
        row_vals = [df.iloc[r_idx, c_idx] if c_idx < df.shape[1] else None for c_idx in range(df.shape[1])]
        non_empty = [str(v).strip() for v in row_vals if pd.notna(v) and str(v).strip() != '']
        if not non_empty:
            continue

        col0 = str(row_vals[0]).strip() if pd.notna(row_vals[0]) else ''
        col1 = row_vals[1] if len(row_vals) > 1 else None
        col0_lower = col0.lower()

        # Detect Sector header
        if 'top 10 sectors' in col0_lower or (col0_lower == 'sector' and mode is None):
            mode = 'sectors'
            continue

        # Detect Holdings header
        if 'holdings' in col0_lower or col0_lower in ['equity', 'debt', 'security', 'company', 'issuer']:
            mode = 'holdings'
            continue

        # Skip summary/footer rows inside holdings
        if col0_lower.startswith('total') or col0_lower.startswith('grand total') or col0_lower.startswith('others:'):
            continue

        if mode == 'sectors' and col0:
            sectors.append({
                'sector': col0,
                'allocation': str(col1).strip() if pd.notna(col1) and str(col1).strip() != '' else ''
            })
        elif mode == 'holdings' and col0:
            holdings.append({
                'holding': col0,
                'allocation': str(col1).strip() if pd.notna(col1) and str(col1).strip() != '' else ''
            })

    return {
        'fund': fund_name,
        'sectors': sectors,
        'holdings': holdings,
    }


def parse_category_workbook(file_obj, category):
    """
    Parses multi-sheet Excel workbooks:
    - Sheet 1 (index 0): Summary performance table stored in SQL (`<category>_funds`)
    - Sheets 2..N: Individual fund portfolio sheets where Cell A1 holds the exact full fund name
    """
    excel_file = pd.ExcelFile(file_obj)
    sheet_names = excel_file.sheet_names
    if not sheet_names:
        return

    # Sheet 1: Summary performance table
    summary_df = pd.read_excel(excel_file, sheet_name=sheet_names[0])
    table_name = f'{category}_funds'
    if engine:
        summary_df.to_sql(table_name, engine, if_exists='replace', index=False)

    # Individual fund sheets (Sheet 2 onward)
    store = load_portfolio_store()
    cat_store = {}
    for sname in sheet_names[1:]:
        try:
            sdf = pd.read_excel(excel_file, sheet_name=sname, header=None)
            parsed = _parse_single_fund_sheet(sdf)
            if parsed and parsed.get('fund'):
                cat_store[parsed['fund']] = parsed
        except Exception as e:
            print(f"Error parsing portfolio sheet '{sname}' in {category}: {e}")

    store[category] = cat_store
    save_portfolio_store(store)


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
                        'y4': format_pct(row.iloc[9]) if len(row) > 9 else '0',
                        'y5': format_pct(row.iloc[10]) if len(row) > 10 else '0',
                        'y7': format_pct(row.iloc[11]) if len(row) > 11 else '0',
                        'y10': format_pct(row.iloc[12]) if len(row) > 12 else '0',
                        'high': str(row.iloc[13]) if len(row) > 13 else '0',
                        'latest': str(row.iloc[14]) if len(row) > 14 else '0',
                    })
    except Exception:
        pass
    return fund_list
<<<<<<< HEAD


def get_fund_full_record(category, fund_name):
    cat_key = (category or '').lower()
    table_map = {
        'equity': 'equity_funds',
        'balancer': 'balancer_funds',
        'debt': 'debt_funds',
    }
    table_name = table_map.get(cat_key)
    perf_row = None
    if table_name:
        rows = parse_fund_excel_from_db(table_name)
        target_clean = fund_name.strip().lower()
        perf_row = next((r for r in rows if str(r.get('fund', '')).strip().lower() == target_clean), None)

    store = load_portfolio_store()
    cat_portfolios = store.get(cat_key, {})
    portfolio_entry = None
    for k, v in cat_portfolios.items():
        if str(k).strip().lower() == fund_name.strip().lower():
            portfolio_entry = v
            break

    return perf_row, portfolio_entry


def is_today_filename(filename, upload_timestamp=None):
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    today_patterns = [ist_now.strftime('%d-%m-%Y'), ist_now.strftime('%d_%m_%Y'), ist_now.strftime('%d.%m.%Y')]
    for pattern in today_patterns:
        if pattern in filename.lower():
            return True
    if upload_timestamp:
        try:
            dt = datetime.fromisoformat(upload_timestamp)
            if dt.date() == ist_now.date():
                return True
        except Exception:
            pass
    return False


def extract_date_from_filename(filename):
    fn = filename.lower()
    clean_name = os.path.splitext(filename)[0]
    for fmt in ('%d-%m-%Y', '%d_%m_%Y', '%Y-%m-%d', '%Y_%m_%d', '%d.%m.%Y', '%d%m%Y'):
        try:
            dt = datetime.strptime(clean_name, fmt)
            return dt.strftime('%Y'), dt.strftime('%B')
        except ValueError:
            continue
    year = datetime.now().strftime('%Y')
    match_year = re.search(r'(20\d{2})', fn)
    if match_year:
        year = match_year.group(1)
    month = datetime.now().strftime('%B')
    month_map = {'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April', 'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August', 'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'}
    for k, v in month_map.items():
        if k in fn:
            month = v
            break
    return year, month
=======
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
              'y4': format_pct(row.iloc[9]) if len(row) > 9 else '0',
              'y5': format_pct(row.iloc[10]) if len(row) > 10 else '0',
              'y7': format_pct(row.iloc[11]) if len(row) > 11 else '0',
              'y10': format_pct(row.iloc[12]) if len(row) > 12 else '0',
              'high': str(row.iloc[13]) if len(row) > 13 else '0',
              'latest': str(row.iloc[14]) if len(row) > 14 else '0',
          })
  except Exception as e:
    print(f'Error reading table {table_name} from Supabase: {e}')
  return fund_list


def is_today_filename(filename, upload_timestamp=None):
  now_utc = datetime.now(timezone.utc)
  ist_now = now_utc + timedelta(hours=5, minutes=30)
  
  today_patterns = [
      ist_now.strftime('%d-%m-%Y'),
      ist_now.strftime('%d_%m_%Y'),
      ist_now.strftime('%d.%m.%Y'),
      ist_now.strftime('%Y-%m-%d'),
      ist_now.strftime('%Y_%m_%d'),
  ]
  
  fn = filename.lower()
  for pattern in today_patterns:
    if pattern in fn:
      return True

  if upload_timestamp:
    try:
      dt = datetime.fromisoformat(upload_timestamp)
      if dt.date() == ist_now.date():
        return True
    except Exception:
      pass

  return False


def extract_date_from_filename(filename):
  fn = filename.lower()
  clean_name = os.path.splitext(filename)[0]
  
  for fmt in ('%d-%m-%Y', '%d_%m_%Y', '%m-%d-%Y', '%m_%d_%Y', '%Y-%m-%d', '%Y_%m_%d', '%d.%m.%Y', '%d%m%Y'):
    try:
      dt = datetime.strptime(clean_name, fmt)
      return dt.strftime('%Y'), dt.strftime('%B')
    except ValueError:
      continue

  year = datetime.now().strftime('%Y')
  match_year = re.search(r'(20\d{2})', fn)
  if match_year:
    year = match_year.group(1)

  month = datetime.now().strftime('%B')
  month_map = {
      'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April',
      'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August',
      'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December',
      'january': 'January', 'february': 'February', 'march': 'March', 'april': 'April',
      'june': 'June', 'july': 'July', 'august': 'August', 'september': 'September',
      'october': 'October', 'november': 'November', 'december': 'December'
  }
  for k, v in month_map.items():
    if k in fn:
      month = v
      break
  return year, month
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/')
def home():
<<<<<<< HEAD
    if validate_and_restore_auto_session():
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))
=======
  return redirect(url_for('login'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/health')
def health_check():
<<<<<<< HEAD
    return 'OK', 200
=======
  return 'OK', 200
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
<<<<<<< HEAD
    if request.method == 'GET' and validate_and_restore_auto_session():
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        step = request.form.get('step', 'request_code')
        username = request.form.get('username', '').strip()
        mobile = request.form.get('mobile', '').strip()

        name_is_valid = bool(re.match(r'^[A-Za-z\s]+$', username))
        clean_mobile = re.sub(r'\D', '', mobile)
        mobile_is_valid = 10 <= len(clean_mobile) <= 12

        if not name_is_valid or not mobile_is_valid:
            flash('Use correct name (letters only) and valid mobile number.', 'danger')
            return render_template('login.html', step='request_code', display_code='')

        if step == 'request_code':
            display_code = str(random.randint(1000, 9999))
            PENDING_OTPS[mobile] = display_code
            return render_template('login.html', step='verify_code', username=username, mobile=mobile, display_code=display_code)

        elif step == 'verify_code':
            entered_code = request.form.get('code', '').strip()
            display_code = request.form.get('display_code', '').strip()
            if mobile in PENDING_OTPS and PENDING_OTPS[mobile] == entered_code:
                del PENDING_OTPS[mobile]
                session.permanent = True
                session['username'] = username
                session['mobile'] = mobile

                now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                login_time_str = now_ist.strftime('%b %d, %Y, %I:%M %p')
                now_local = datetime.now()

                user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
                if not user_record:
                    user_record = {
                        'id': len(REGISTERED_USERS) + 1,
                        'name': username,
                        'mobile': mobile,
                        'status': 'Pending',
                        'registered_at': now_local,
                        'approved_at': None,
                        'session_started_at': now_local,
                        'last_login': login_time_str,
                        'last_active': now_local,
                    }
                    REGISTERED_USERS.append(user_record)
                else:
                    user_record['last_login'] = login_time_str
                    user_record['last_active'] = now_local
                    check_user_validity(user_record)
                    if user_record['status'] == 'Approved' and not user_record.get('session_started_at'):
                        user_record['session_started_at'] = now_local

                send_whatsapp_alert(f"🔐 *User Login Alert*\n\n*Name:* {username}\n*Mobile:* {mobile}\n*Status:* {user_record['status']}")

                if user_record['status'] == 'Pending':
                    return redirect(url_for('pending_approval'))

                resp = make_response(redirect(url_for('user_dashboard')))
                issue_auto_login_cookie(resp, username, mobile, is_admin=False)
                return resp
            else:
                flash('Invalid code entered. Please type the correct displayed code.', 'danger')
                return render_template('login.html', step='verify_code', username=username, mobile=mobile, display_code=display_code)

    return render_template('login.html', step='request_code', display_code='')


@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('login')))
    return revoke_auto_login_cookie(resp)
=======
  if request.method == 'POST':
    step = request.form.get('step', 'request_code')
    username = request.form.get('username', '').strip()
    mobile = request.form.get('mobile', '').strip()

    name_is_valid = bool(re.match(r'^[A-Za-z\s]+$', username))
    clean_mobile = re.sub(r'\D', '', mobile)
    mobile_is_valid = 10 <= len(clean_mobile) <= 12

    if not name_is_valid or not mobile_is_valid:
      flash('Use correct name (letters only) and valid mobile number.', 'danger')
      return render_template('login.html', step='request_code', display_code='')

    if step == 'request_code':
      display_code = str(random.randint(1000, 9999))
      PENDING_OTPS[mobile] = display_code
      return render_template('login.html', step='verify_code', username=username, mobile=mobile, display_code=display_code)

    elif step == 'verify_code':
      entered_code = request.form.get('code', '').strip()
      display_code = request.form.get('display_code', '').strip()
      if mobile in PENDING_OTPS and PENDING_OTPS[mobile] == entered_code:
        del PENDING_OTPS[mobile]
        session.permanent = True
        session['username'] = username
        session['mobile'] = mobile
        user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
        if not user_record:
          user_record = {
              'id': len(REGISTERED_USERS) + 1,
              'name': username,
              'mobile': mobile,
              'status': 'Pending',
              'registered_at': datetime.now(),
              'approved_at': None,
          }
          REGISTERED_USERS.append(user_record)
        else:
          check_user_validity(user_record)
        if user_record['status'] == 'Pending':
          return redirect(url_for('pending_approval'))
        return redirect(url_for('user_dashboard'))
      else:
        flash('Invalid code entered. Please type the correct displayed code.', 'danger')
        return render_template('login.html', step='verify_code', username=username, mobile=mobile, display_code=display_code)

  return render_template('login.html', step='request_code', display_code='')
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/pending-approval')
def pending_approval():
<<<<<<< HEAD
    validate_and_restore_auto_session()
    mobile = session.get('mobile', '')
    user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
    if user_record:
        check_user_validity(user_record)
        if user_record['status'] == 'Approved':
            resp = make_response(redirect(url_for('user_dashboard')))
            issue_auto_login_cookie(resp, user_record['name'], user_record['mobile'], is_admin=False)
            return resp
    return render_template('pending_approval.html', username=session.get('username', 'User'))
=======
  mobile = session.get('mobile', '')
  user_record = next(
      (u for u in REGISTERED_USERS if u['mobile'] == mobile), None
  )
  if user_record:
    check_user_validity(user_record)
    if user_record['status'] == 'Approved':
      return redirect(url_for('user_dashboard'))
  return render_template(
      'pending_approval.html', username=session.get('username', 'User')
  )
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/user-dashboard')
def user_dashboard():
<<<<<<< HEAD
    try:
        validate_and_restore_auto_session()
        mobile = session.get('mobile', '')
        user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
        if user_record:
            user_record['last_active'] = datetime.now()
            check_user_validity(user_record)
            if user_record['status'] == 'Pending':
                return redirect(url_for('pending_approval'))
        if not user_record:
            return redirect(url_for('login'))

        remaining_days = get_remaining_validity_days(user_record)
        market_info, market_trend_data = get_live_market_data()
        admin_online = (datetime.now() - ADMIN_ACTIVITY['last_active']) < timedelta(minutes=5)
        festival_greeting = get_festival_greeting()

        latest_data_updated = False
        latest_filename = 'latest_nav.jpg'
        try:
            meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as mf:
                    meta = json.load(mf)
                    latest_filename = meta.get('filename', 'latest_nav.jpg')
                    last_time = meta.get('upload_time', '')
                    if is_today_filename(latest_filename, last_time):
                        latest_data_updated = True
        except Exception:
            pass

        user_requests = [r for r in DOWNLOAD_REQUESTS if r['username'] == session.get('username')]

        return render_template(
            'user_dashboard.html',
            username=session.get('username', 'Client'),
            mobile=mobile,
            remaining_days=remaining_days,
            market=market_info,
            market_trend=market_trend_data,
            equity_data=parse_fund_excel_from_db('equity_funds'),
            balancer_data=parse_fund_excel_from_db('balancer_funds'),
            debt_data=parse_fund_excel_from_db('debt_funds'),
            latest_data_updated=latest_data_updated,
            admin_online=admin_online,
            festival_greeting=festival_greeting,
            download_requests=user_requests,
            feedbacks=USER_FEEDBACKS,
            latest_filename=latest_filename,
        )
    except Exception:
        return render_template('login.html')


@app.route('/fund/<category>/<path:fund_name>')
def fund_detail_page(category, fund_name):
    validate_and_restore_auto_session()
    if 'username' not in session and not session.get('is_admin'):
        return redirect(url_for('login'))

    decoded_fund = unquote(fund_name)
    perf_row, portfolio_entry = get_fund_full_record(category, decoded_fund)
    if not perf_row:
        perf_row = {
            'fund': decoded_fund,
            'inception': '-',
            'benchmark': '-',
            'since': '0',
            'm1': '0',
            'm6': '0',
            'y1': '0',
            'y2': '0',
            'y3': '0',
            'y4': '0',
            'y5': '0',
            'y7': '0',
            'y10': '0',
            'high': '0',
            'latest': '0',
        }

    sectors = (portfolio_entry or {}).get('sectors', [])
    holdings = (portfolio_entry or {}).get('holdings', [])
    back_url = url_for('admin_dashboard') if session.get('is_admin') else url_for('user_dashboard')

    return render_template(
        'fund_detail.html',
        category=category.capitalize(),
        fund_data=perf_row,
        sectors=sectors,
        holdings=holdings,
        back_url=back_url,
        is_admin=bool(session.get('is_admin')),
        username=session.get('username', 'Admin Bijoosh' if session.get('is_admin') else 'Client'),
    )


@app.route('/api/fund-portfolio/<category>/<path:fund_name>')
def api_fund_portfolio(category, fund_name):
    validate_and_restore_auto_session()
    if 'username' not in session and not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    decoded_fund = unquote(fund_name)
    perf_row, portfolio_entry = get_fund_full_record(category, decoded_fund)
    return jsonify({
        'success': True,
        'fund': decoded_fund,
        'category': category,
        'performance': perf_row,
        'sectors': (portfolio_entry or {}).get('sectors', []),
        'holdings': (portfolio_entry or {}).get('holdings', []),
    })
=======
  try:
    mobile = session.get('mobile', '')
    user_record = next(
        (u for u in REGISTERED_USERS if u['mobile'] == mobile), None
    )
    if user_record:
      check_user_validity(user_record)
      if user_record['status'] == 'Pending':
        return redirect(url_for('pending_approval'))
    if not user_record:
      return redirect(url_for('login'))

    market_info, market_trend_data = get_live_market_data()
    admin_online = (datetime.now() - ADMIN_ACTIVITY['last_active']) < timedelta(minutes=5)
    festival_greeting = get_festival_greeting()

    latest_data_updated = False
    latest_filename = 'latest_nav.jpg'
    try:
      meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
      if os.path.exists(meta_path):
        with open(meta_path, 'r') as mf:
          meta = json.load(mf)
          latest_filename = meta.get('filename', 'latest_nav.jpg')
          last_time = meta.get('upload_time', '')
          if is_today_filename(latest_filename, last_time):
            latest_data_updated = True
    except Exception as e:
      print(f"Error checking upload status: {e}")

    user_requests = [r for r in DOWNLOAD_REQUESTS if r['username'] == session.get('username')]

    return render_template(
        'user_dashboard.html',
        username=session.get('username', 'Client'),
        mobile=mobile,
        market=market_info,
        market_trend=market_trend_data,
        equity_data=parse_fund_excel_from_db('equity_funds'),
        balancer_data=parse_fund_excel_from_db('balancer_funds'),
        debt_data=parse_fund_excel_from_db('debt_funds'),
        latest_data_updated=latest_data_updated,
        admin_online=admin_online,
        admin_mobile=ADMIN_MOBILE,
        festival_greeting=festival_greeting,
        download_requests=user_requests,
        feedbacks=USER_FEEDBACKS,
        latest_filename=latest_filename,
    )
  except Exception as e:
    print(f"Error in user dashboard: {e}")
    return render_template('login.html')
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/request-download', methods=['POST'])
def request_download():
<<<<<<< HEAD
    validate_and_restore_auto_session()
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    data = request.get_json() or {}
    file_name = data.get('filename', 'latest_nav.jpg')
    download_type = data.get('type', 'download')

    req_id = len(DOWNLOAD_REQUESTS) + 1
    username = session.get('username', 'Client')
    DOWNLOAD_REQUESTS.append({
        'id': req_id,
        'username': username,
        'filename': file_name,
        'type': download_type,
        'status': 'Pending',
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    })

    send_whatsapp_alert(f"📥 *Download/View Request (Latest or Old NAV)*\n\n*User:* {username}\n*File:* {file_name}\n*Type:* {download_type}")

    return jsonify({'success': True, 'message': 'Approval request sent to Admin successfully.'})
=======
  if 'username' not in session:
    return jsonify({'success': False, 'message': 'Not logged in'})
  data = request.get_json() or {}
  file_name = data.get('filename', 'latest_nav.jpg')
  download_type = data.get('type', 'download')

  req_id = len(DOWNLOAD_REQUESTS) + 1
  DOWNLOAD_REQUESTS.append({
      'id': req_id,
      'username': session.get('username', 'Client'),
      'filename': file_name,
      'type': download_type,
      'status': 'Pending',
      'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
  })
  return jsonify({
      'success': True,
      'message': 'Approval request sent to Admin successfully.',
  })
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/get-nav-image-base64/<path:filename>')
def get_nav_image_base64(filename):
<<<<<<< HEAD
    validate_and_restore_auto_session()
    if 'username' not in session and not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'})

    username = session.get('username', 'Client')
    target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(target_path):
        for root, dirs, files in os.walk(ARCHIVE_FOLDER):
            if filename in files:
                target_path = os.path.join(root, filename)
                break

    if os.path.exists(target_path):
        send_whatsapp_alert(f"👁️ *NAV Viewed (Latest/Old)*\n\n*User:* {username}\n*File:* {filename}")
        with open(target_path, 'rb') as img_f:
            b64_data = base64.b64encode(img_f.read()).decode('utf-8')
        return jsonify({'success': True, 'image_data': f"data:image/jpeg;base64,{b64_data}"})
    return jsonify({'success': False, 'message': 'Image not found'})
=======
  if 'username' not in session and not session.get('is_admin'):
    return jsonify({'success': False, 'message': 'Unauthorized'})
  
  target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
  if not os.path.exists(target_path):
    archive_base = ARCHIVE_FOLDER
    for root, dirs, files in os.walk(archive_base):
      if filename in files:
        target_path = os.path.join(root, filename)
        break

  if os.path.exists(target_path):
    import base64
    with open(target_path, 'rb') as img_f:
      b64_data = base64.b64encode(img_f.read()).decode('utf-8')
    return jsonify({'success': True, 'image_data': f"data:image/jpeg;base64,{b64_data}"})
  
  return jsonify({'success': False, 'message': 'Image not found'})
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/view-archive-secured/<path:filename>')
def view_archive_secured(filename):
<<<<<<< HEAD
    validate_and_restore_auto_session()
    if 'username' not in session and not session.get('is_admin'):
        return redirect(url_for('login'))

    username = session.get('username', 'Client')
    if session.get('is_admin'):
        for root, dirs, files in os.walk(ARCHIVE_FOLDER):
            if filename in files:
                return send_from_directory(root, filename)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    approved_req = next((r for r in DOWNLOAD_REQUESTS if r['username'] == session.get('username') and r['filename'] == filename and r['status'] == 'Approved'), None)
    if approved_req:
        send_whatsapp_alert(f"👁️ *Secured NAV / Archive Viewed or Downloaded*\n\n*User:* {username}\n*File:* {filename}")
        for root, dirs, files in os.walk(ARCHIVE_FOLDER):
            if filename in files:
                return send_from_directory(root, filename)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    flash('Download requires Admin Approval.', 'warning')
    return redirect(url_for('user_dashboard'))
=======
  if 'username' not in session and not session.get('is_admin'):
    return redirect(url_for('login'))
  
  if session.get('is_admin'):
    archive_base = ARCHIVE_FOLDER
    for root, dirs, files in os.walk(archive_base):
      if filename in files:
        return send_from_directory(root, filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

  approved_req = next((r for r in DOWNLOAD_REQUESTS if r['username'] == session.get('username') and r['filename'] == filename and r['status'] == 'Approved' and r['type'] == 'download'), None)
  if approved_req:
    archive_base = ARCHIVE_FOLDER
    for root, dirs, files in os.walk(archive_base):
      if filename in files:
        return send_from_directory(root, filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
  
  flash('Download requires Admin Approval. Request submitted.', 'warning')
  return redirect(url_for('user_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
<<<<<<< HEAD
    validate_and_restore_auto_session()
    if 'username' not in session:
        return redirect(url_for('login'))
    feedback_text = request.form.get('feedback')
    rating = request.form.get('rating', '5')
    if feedback_text:
        username = session.get('username', 'Client')
        USER_FEEDBACKS.append({
            'id': len(USER_FEEDBACKS) + 1,
            'username': username,
            'feedback': feedback_text,
            'rating': int(rating) if str(rating).isdigit() else 5,
            'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
        })
        send_whatsapp_alert(f"⭐ *New Feedback Received*\n\n*User:* {username}\n*Rating:* {rating}/5\n*Feedback:* {feedback_text}")
        flash('Feedback submitted successfully!', 'success')
    return redirect(url_for('user_dashboard'))
=======
  if 'username' not in session:
    return redirect(url_for('login'))
  feedback_text = request.form.get('feedback')
  rating = request.form.get('rating', '5')
  if feedback_text:
    USER_FEEDBACKS.append({
        'id': len(USER_FEEDBACKS) + 1,
        'username': session.get('username', 'Client'),
        'feedback': feedback_text,
        'rating': int(rating) if str(rating).isdigit() else 5,
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    })
    flash('Feedback submitted successfully!', 'success')
  return redirect(url_for('user_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/admin-login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def admin_login():
<<<<<<< HEAD
    if request.method == 'POST':
        mobile_input = request.form.get('mobile')
        password_input = request.form.get('password')
        if mobile_input == '+918078535666' and password_input == 'Bichu@5419':
            session.permanent = True
            session['is_admin'] = True
            ADMIN_ACTIVITY['last_active'] = datetime.now()
            send_whatsapp_alert("🛡️ *Admin Login Alert*\n\nAdmin successfully logged into the control panel.")
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid Admin Credentials', 'danger')
    return render_template('admin_login.html')
=======
  if request.method == 'POST':
    mobile_input = request.form.get('mobile')
    password_input = request.form.get('password')
    if mobile_input == '+918078535666' and password_input == 'Bichu@5419':
      session.permanent = True
      session['is_admin'] = True
      ADMIN_ACTIVITY['last_active'] = datetime.now()
      return redirect(url_for('admin_dashboard'))
    else:
      flash('Invalid Admin Credentials', 'danger')
  return render_template('admin_login.html')
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/admin')
def admin_redirect():
<<<<<<< HEAD
    validate_and_restore_auto_session()
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))
=======
  if session.get('is_admin'):
    return redirect(url_for('admin_dashboard'))
  return redirect(url_for('admin_login'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/admin-dashboard', methods=['GET', 'POST'])
def admin_dashboard():
<<<<<<< HEAD
    validate_and_restore_auto_session()
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    for user in REGISTERED_USERS:
        check_user_validity(user)
        user['is_online'] = (datetime.now() - user.get('last_active', datetime.min)) < timedelta(minutes=5)

    market_info, market_trend_data = get_live_market_data()
    festival_greeting = get_festival_greeting()
    user_filter = request.args.get('user_filter', 'all')
    req_filter = request.args.get('req_filter', 'all')

    filtered_requests = DOWNLOAD_REQUESTS
    if req_filter != 'all':
        filtered_requests = [r for r in DOWNLOAD_REQUESTS if r['status'].lower() == req_filter.lower()]

    return render_template(
        'admin_dashboard.html',
        market=market_info,
        market_trend=market_trend_data,
        users=REGISTERED_USERS,
        feedbacks=USER_FEEDBACKS,
        download_requests=filtered_requests,
        req_filter=req_filter,
        chat_messages=CHAT_MESSAGES,
        equity_data=parse_fund_excel_from_db('equity_funds'),
        balancer_data=parse_fund_excel_from_db('balancer_funds'),
        debt_data=parse_fund_excel_from_db('debt_funds'),
        auto_approval_enabled=ADMIN_SETTINGS['auto_approval_enabled'],
        current_time=datetime.now().strftime('%b %d, %Y, %I:%M:%S %p'),
        festival_greeting=festival_greeting,
        user_filter=user_filter,
    )
=======
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  
  ADMIN_ACTIVITY['last_active'] = datetime.now()

  for user in REGISTERED_USERS:
    check_user_validity(user)

  market_info, market_trend_data = get_live_market_data()
  festival_greeting = get_festival_greeting()
  user_filter = request.args.get('user_filter', 'all')

  return render_template(
      'admin_dashboard.html',
      market=market_info,
      market_trend=market_trend_data,
      users=REGISTERED_USERS,
      feedbacks=USER_FEEDBACKS,
      download_requests=DOWNLOAD_REQUESTS,
      equity_data=parse_fund_excel_from_db('equity_funds'),
      balancer_data=parse_fund_excel_from_db('balancer_funds'),
      debt_data=parse_fund_excel_from_db('debt_funds'),
      auto_approval_enabled=ADMIN_SETTINGS['auto_approval_enabled'],
      current_time=datetime.now().strftime('%b %d, %Y, %I:%M:%S %p'),
      festival_greeting=festival_greeting,
      user_filter=user_filter,
  )
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/admin/approve-download/<int:req_id>', methods=['POST'])
def approve_download(req_id):
<<<<<<< HEAD
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    for req in DOWNLOAD_REQUESTS:
        if req['id'] == req_id:
            req['status'] = 'Approved'
            flash("Download request approved!", 'success')
            break
    return redirect(url_for('admin_dashboard'))
=======
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  for req in DOWNLOAD_REQUESTS:
    if req['id'] == req_id:
      req['status'] = 'Approved'
      flash(f"Download request for {req['filename']} approved!", 'success')
      break
  return redirect(url_for('admin_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/admin/reject-download/<int:req_id>', methods=['POST'])
def reject_download(req_id):
<<<<<<< HEAD
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    for req in DOWNLOAD_REQUESTS:
        if req['id'] == req_id:
            req['status'] = 'Rejected'
            flash("Download request rejected.", 'danger')
            break
    return redirect(url_for('admin_dashboard'))
=======
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  for req in DOWNLOAD_REQUESTS:
    if req['id'] == req_id:
      req['status'] = 'Rejected'
      flash(f"Download request for {req['filename']} rejected.", 'danger')
      break
  return redirect(url_for('admin_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/toggle-auto-approval', methods=['POST'])
def toggle_auto_approval():
<<<<<<< HEAD
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    ADMIN_SETTINGS['auto_approval_enabled'] = not ADMIN_SETTINGS.get('auto_approval_enabled', True)
    status_text = "Enabled" if ADMIN_SETTINGS['auto_approval_enabled'] else "Disabled"
    flash(f'Auto-approval has been {status_text} successfully!', 'success')
    return redirect(url_for('admin_dashboard'))
=======
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  ADMIN_SETTINGS['auto_approval_enabled'] = not ADMIN_SETTINGS.get('auto_approval_enabled', True)
  status_text = "Enabled" if ADMIN_SETTINGS['auto_approval_enabled'] else "Disabled"
  flash(f'Auto-approval has been {status_text} successfully!', 'success')
  return redirect(url_for('admin_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/update-user-status/<int:user_id>/<status>', methods=['POST'])
def update_user_status(user_id, status):
<<<<<<< HEAD
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    for user in REGISTERED_USERS:
        if user['id'] == user_id:
            normalized = status.capitalize()
            user['status'] = normalized
            if normalized == 'Approved':
                now_dt = datetime.now()
                user['approved_at'] = now_dt.isoformat()
                user['session_started_at'] = now_dt
            else:
                user['approved_at'] = None
                for tok, entry in AUTO_LOGIN_TOKENS.items():
                    if entry.get('mobile') == user.get('mobile'):
                        entry['revoked'] = True
    return redirect(url_for('admin_dashboard'))
=======
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  
  ADMIN_ACTIVITY['last_active'] = datetime.now()

  for user in REGISTERED_USERS:
    if user['id'] == user_id:
      user['status'] = status.capitalize()
      if status.capitalize() == 'Approved':
        user['approved_at'] = datetime.now().isoformat()
      else:
        user['approved_at'] = None
  return redirect(url_for('admin_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/approve-all-users', methods=['POST'])
def approve_all_users():
<<<<<<< HEAD
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    now_dt = datetime.now()
    now_iso = now_dt.isoformat()
    for user in REGISTERED_USERS:
        if user['status'] == 'Pending':
            user['status'] = 'Approved'
            user['approved_at'] = now_iso
            user['session_started_at'] = now_dt
    flash('All pending users approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))
=======
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  
  ADMIN_ACTIVITY['last_active'] = datetime.now()
  now_iso = datetime.now().isoformat()
  for user in REGISTERED_USERS:
    if user['status'] == 'Pending':
      user['status'] = 'Approved'
      user['approved_at'] = now_iso
  flash('All pending users approved successfully!', 'success')
  return redirect(url_for('admin_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/decline-all-users', methods=['POST'])
def decline_all_users():
<<<<<<< HEAD
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    for user in REGISTERED_USERS:
        if user['status'] == 'Pending':
            user['status'] = 'Pending'
    flash('All pending users declined successfully!', 'success')
    return redirect(url_for('admin_dashboard'))
=======
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  
  ADMIN_ACTIVITY['last_active'] = datetime.now()
  for user in REGISTERED_USERS:
    if user['status'] == 'Pending':
      user['status'] = 'Pending'
      user['approved_at'] = None
  flash('All pending users declined successfully!', 'success')
  return redirect(url_for('admin_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/upload-master-category', methods=['GET', 'POST'])
def upload_master_category():
<<<<<<< HEAD
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    if request.method == 'POST':
        try:
            category = request.form.get('category')
            file_key = f'{category}_file'
            if file_key in request.files:
                file = request.files[file_key]
                if file and file.filename != '':
                    parse_category_workbook(file, category)
                    flash(f'{category.capitalize()} funds and portfolio sheets updated permanently!', 'success')
        except Exception as e:
            flash(f'Error updating category: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))
=======
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  
  ADMIN_ACTIVITY['last_active'] = datetime.now()

  if request.method == 'POST':
    try:
      category = request.form.get('category')
      file_key = f'{category}_file'
      if file_key in request.files:
        file = request.files[file_key]
        if file and file.filename != '':
          df = pd.read_excel(file)
          table_name = f'{category}_funds'
          if engine:
            df.to_sql(table_name, engine, if_exists='replace', index=False)
            flash(f'{category.capitalize()} funds updated permanently in Supabase database!', 'success')
          else:
            flash('Database connection error.', 'danger')
    except Exception as e:
      flash(f'Error updating category: {e}', 'danger')
  return redirect(url_for('admin_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/upload-nav', methods=['GET', 'POST'])
def upload_nav():
<<<<<<< HEAD
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    if request.method == 'POST':
        try:
            if 'nav_image' not in request.files:
                flash('No file part in the request.', 'danger')
                return redirect(url_for('admin_dashboard'))

            file = request.files.get('nav_image')
            if not file or file.filename == '':
                flash('No image selected for uploading.', 'danger')
                return redirect(url_for('admin_dashboard'))

            raw_fn = file.filename
            filename = secure_filename(raw_fn) or f'{datetime.now().strftime("%d-%m-%Y")}.jpg'
            file_path_upload = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            latest_ref_path = os.path.join(app.config['UPLOAD_FOLDER'], 'latest_nav.jpg')

            try:
                file.save(file_path_upload)
                shutil.copy(file_path_upload, latest_ref_path)
            except Exception as save_err:
                print(f"File save error: {save_err}")
                flash(f'Error saving file: {save_err}', 'danger')
                return redirect(url_for('admin_dashboard'))

            meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
            try:
                with open(meta_path, 'w') as mf:
                    json.dump({'filename': filename, 'original_filename': raw_fn, 'upload_time': datetime.now().isoformat()}, mf)
            except Exception:
                pass

            try:
                target_year, target_month = extract_date_from_filename(raw_fn)
                archive_target_dir = os.path.join(ARCHIVE_FOLDER, target_year, target_month)
                os.makedirs(archive_target_dir, exist_ok=True)
                shutil.copy(file_path_upload, os.path.join(archive_target_dir, filename))
            except Exception as arc_err:
                print(f"Archive copy warning: {arc_err}")

            flash(f'Successfully published NAV: {filename}', 'success')
        except Exception as e:
            print(f"Critical upload error: {e}")
            flash(f'Error uploading NAV image: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))
=======
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  
  ADMIN_ACTIVITY['last_active'] = datetime.now()

  if request.method == 'POST':
    try:
      file = request.files.get('nav_image')
      if file and file.filename != '':
        raw_fn = file.filename
        filename = secure_filename(raw_fn)
        if not filename:
          filename = f'{datetime.now().strftime("%d-%m-%Y")}.jpg'

        file_bytes = file.read()
        
        file_path_upload = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(file_path_upload, 'wb') as f:
          f.write(file_bytes)
        
        latest_ref_path = os.path.join(app.config['UPLOAD_FOLDER'], 'latest_nav.jpg')
        with open(latest_ref_path, 'wb') as f:
          f.write(file_bytes)

        meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
        with open(meta_path, 'w') as mf:
          json.dump({
              'filename': filename,
              'original_filename': raw_fn,
              'upload_time': datetime.now().isoformat()
          }, mf)

        target_year, target_month = extract_date_from_filename(raw_fn)
        archive_target_dir = os.path.join(ARCHIVE_FOLDER, target_year, target_month)
        os.makedirs(archive_target_dir, exist_ok=True)
        archive_file_path = os.path.join(archive_target_dir, filename)
        with open(archive_file_path, 'wb') as f:
          f.write(file_bytes)

        flash(f'Successfully published NAV: {filename} (Archived to {target_year}/{target_month})', 'success')
      else:
        flash('No file selected for NAV upload.', 'warning')
    except Exception as e:
      flash(f'Error uploading NAV image: {e}', 'danger')
  return redirect(url_for('admin_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/upload-archive', methods=['GET', 'POST'])
def upload_archive():
<<<<<<< HEAD
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    if request.method == 'POST':
        try:
            year = request.form.get('archive_year', datetime.now().strftime('%Y'))
            month_input = request.form.get('archive_month', 'Oct').strip().lower()
            month_map = {'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April', 'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August', 'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'}
            full_month_name = month_map.get(month_input[:3], 'October')
            saved_count = 0
            for file in request.files.getlist('archive_files'):
                if file and file.filename != '':
                    raw_fn = file.filename
                    filename = secure_filename(raw_fn)
                    f_year, f_month = extract_date_from_filename(raw_fn)
                    target_dir = os.path.join(ARCHIVE_FOLDER, f_year or year, f_month or full_month_name)
                    os.makedirs(target_dir, exist_ok=True)
                    file_path = os.path.join(target_dir, filename)
                    file.save(file_path)
                    shutil.copy(file_path, os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    saved_count += 1
            flash(f'Successfully uploaded {saved_count} archive file(s)!', 'success')
        except Exception as e:
            flash(f'Error uploading archive files: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))
=======
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  
  ADMIN_ACTIVITY['last_active'] = datetime.now()

  if request.method == 'POST':
    try:
      year = request.form.get('archive_year', datetime.now().strftime('%Y'))
      month_input = request.form.get('archive_month', 'Oct').strip().lower()

      month_map = {
          'jan': 'January', 'feb': 'February', 'mar': 'March',
          'apr': 'April', 'may': 'May', 'jun': 'June',
          'jul': 'July', 'aug': 'August', 'sep': 'September',
          'oct': 'October', 'nov': 'November', 'dec': 'December'
      }
      full_month_name = month_map.get(month_input[:3], 'October')

      saved_count = 0
      files = request.files.getlist('archive_files')
      for file in files:
        if file and file.filename != '':
          raw_fn = file.filename
          filename = secure_filename(raw_fn)
          if not filename:
            filename = f'{datetime.now().strftime("%d-%m-%Y")}.jpg'

          f_year, f_month = extract_date_from_filename(raw_fn)
          target_year = f_year if f_year else year
          target_month = f_month if f_month else full_month_name

          target_dir = os.path.join(ARCHIVE_FOLDER, target_year, target_month)
          os.makedirs(target_dir, exist_ok=True)
          file_path = os.path.join(target_dir, filename)
          file.save(file_path)
          
          upload_mirror_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
          shutil.copy(file_path, upload_mirror_path)
          
          saved_count += 1

      if saved_count > 0:
        flash(f'Successfully uploaded {saved_count} archive file(s) and synced to folders!', 'success')
      else:
        flash('No files selected for archive upload.', 'warning')
    except Exception as e:
      flash(f'Error uploading archive files: {e}', 'danger')
  return redirect(url_for('admin_dashboard'))


@app.route('/delete-archive-file/<filename>', methods=['POST'])
def delete_archive_file(filename):
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  
  ADMIN_ACTIVITY['last_active'] = datetime.now()

  try:
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
      os.remove(file_path)
      flash(f'Successfully deleted: {filename}', 'success')
    else:
      flash('File not found.', 'danger')
  except Exception as e:
    flash(f'Error deleting file: {e}', 'danger')
  return redirect(url_for('admin_dashboard'))
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)


@app.route('/get-archive-files', methods=['GET'])
def get_archive_files():
<<<<<<< HEAD
    year = request.args.get('year', '').strip()
    month_input = request.args.get('month', '').strip().lower()
    month_map = {'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April', 'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August', 'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'}
    full_month = month_map.get(month_input[:3], month_input.capitalize())
    target_dir = os.path.join(ARCHIVE_FOLDER, year, full_month)
    matched_files = []
    if os.path.exists(target_dir):
        try:
            for f in os.listdir(target_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                    matched_files.append(f)
        except Exception:
            pass
    return jsonify({'success': True, 'files': sorted(list(set(matched_files)), reverse=True)})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
=======
  year = request.args.get('year', '').strip()
  month_input = request.args.get('month', '').strip().lower()
  matched_files = []

  month_map = {
      'jan': 'January', 'feb': 'February', 'mar': 'March',
      'apr': 'April', 'may': 'May', 'jun': 'June',
      'jul': 'July', 'aug': 'August', 'sep': 'September',
      'october': 'October', 'november': 'November', 'december': 'December',
      'january': 'January', 'february': 'February', 'march': 'March', 'april': 'April',
      'june': 'June', 'july': 'July', 'august': 'August', 'september': 'September',
      'october': 'October', 'november': 'November', 'december': 'December'
  }
  full_month = month_map.get(month_input[:3], month_input.capitalize())

  target_dir = os.path.join(ARCHIVE_FOLDER, year, full_month)

  if os.path.exists(target_dir):
    try:
      for f in os.listdir(target_dir):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
          matched_files.append(f)
    except Exception as e:
      print(f'Error reading archive directory: {e}')

  sorted_files = sorted(list(set(matched_files)), reverse=True)
  return jsonify({'success': True, 'files': sorted_files})


if __name__ == '__main__':
  app.run(debug=True)
>>>>>>> 45aef26 (Update indices, zoom modal, and login security)
