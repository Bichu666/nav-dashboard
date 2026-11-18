import base64
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
import random
import re
import shutil
import smtplib
import threading
import time
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
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
import pandas as pd
from PIL import Image
import requests
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename
import yfinance as yf

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'nav_updates_persistent_secret_key_2026')

app.permanent_session_lifetime = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=['10000 per day', '1000 per hour'],
    storage_uri='memory://',
)

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL) if DATABASE_URL else None

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ARCHIVE_FOLDER = 'archive_nav'
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

CHAT_FILE = 'chat_messages.json'
USERS_FILE = 'registered_users.json'
REQUESTS_FILE = 'download_requests.json'

ADMIN_ACTIVITY = {'last_active': datetime.now()}

ADMIN_COOKIE_NAME = 'nav_admin_session'
USER_COOKIE_NAME = 'nav_user_session'
auth_serializer = URLSafeTimedSerializer(app.secret_key)


def set_admin_cookie(response):
    token = auth_serializer.dumps({
        'is_admin': True,
        'role': 'admin',
        'ts': datetime.now().isoformat(),
    })
    response.set_cookie(
        ADMIN_COOKIE_NAME,
        token,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite='Lax',
        path='/',
    )
    return response


def clear_admin_cookie(response):
    response.delete_cookie(ADMIN_COOKIE_NAME, path='/')
    return response


def set_user_cookie(response, username, mobile, login_ts):
    token = auth_serializer.dumps({
        'username': username,
        'mobile': mobile,
        'role': 'user',
        'login_ts': login_ts,
    })
    response.set_cookie(
        USER_COOKIE_NAME,
        token,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite='Lax',
        path='/',
    )
    return response


def get_user_auth():
    token = request.cookies.get(USER_COOKIE_NAME)
    if token:
        try:
            data = auth_serializer.loads(token, max_age=30 * 24 * 3600)
            if data.get('username') and data.get('mobile'):
                return data
        except (BadSignature, SignatureExpired, Exception):
            pass
    if session.get('user_username') and session.get('user_mobile'):
        return {
            'username': session.get('user_username'),
            'mobile': session.get('user_mobile'),
            'role': 'user',
            'login_ts': session.get('user_login_ts') or datetime.now().isoformat(),
        }
    return None


def is_admin_authenticated():
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if token:
        try:
            data = auth_serializer.loads(token, max_age=30 * 24 * 3600)
            if data.get('is_admin'):
                return True
        except (BadSignature, SignatureExpired, Exception):
            pass
    if session.get('admin_authenticated') is True:
        return True
    return False


ADMIN_SETTINGS = {'auto_approval_enabled': True}
ADMIN_EMAIL = 'bijooshpadmakumar522@gmail.com'
ADMIN_MOBILE = '+918078535666'

DEFAULT_USERS = [
    {
        'id': 1,
        'name': 'Rahul Sharma',
        'mobile': '+91 9876543210',
        'status': 'Pending',
        'registered_at': (datetime.now() - timedelta(minutes=3)).isoformat(),
        'approved_at': None,
        'last_seen': None,
        'is_online': False,
    },
    {
        'id': 2,
        'name': 'Priya Nair',
        'mobile': '+91 9876522888',
        'status': 'Approved',
        'registered_at': (datetime.now() - timedelta(days=5)).isoformat(),
        'approved_at': datetime.now().isoformat(),
        'last_seen': None,
        'is_online': False,
    },
    {
        'id': 3,
        'name': 'biju',
        'mobile': '+917034788666',
        'status': 'Approved',
        'registered_at': (datetime.now() - timedelta(days=10)).isoformat(),
        'approved_at': datetime.now().isoformat(),
        'last_seen': None,
        'is_online': False,
    },
]


def load_registered_users():
    users = []
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                if isinstance(raw, list) and raw:
                    users = raw
        except Exception as e:
            print(f'Error loading registered users: {e}')
    if not users:
        users = json.loads(json.dumps(DEFAULT_USERS))
    for u in users:
        for dt_key in ('registered_at', 'last_seen'):
            val = u.get(dt_key)
            if isinstance(val, str) and val:
                try:
                    u[dt_key] = datetime.fromisoformat(val)
                except Exception:
                    u[dt_key] = datetime.now() if dt_key == 'registered_at' else None
    return users


def save_registered_users():
    try:
        serializable = []
        for u in REGISTERED_USERS:
            item = dict(u)
            for dt_key in ('registered_at', 'last_seen'):
                val = item.get(dt_key)
                if isinstance(val, datetime):
                    item[dt_key] = val.isoformat()
            serializable.append(item)
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        print(f'Error saving registered users: {e}')


REGISTERED_USERS = load_registered_users()
save_registered_users()


def load_download_requests():
    if os.path.exists(REQUESTS_FILE):
        try:
            with open(REQUESTS_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                if isinstance(raw, list):
                    return raw
        except Exception as e:
            print(f'Error loading download requests: {e}')
    return [
        {
            'id': 1,
            'username': 'Rahul Sharma',
            'filename': 'latest_nav.jpg',
            'type': 'download',
            'status': 'Pending',
            'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
        }
    ]


def save_download_requests():
    try:
        with open(REQUESTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(DOWNLOAD_REQUESTS[-500:], f, indent=2)
    except Exception as e:
        print(f'Error saving download requests: {e}')


DOWNLOAD_REQUESTS = load_download_requests()
save_download_requests()


def ensure_user_record(username, mobile, preserve_approved=True):
    clean_mob = re.sub(r'\D', '', str(mobile or ''))
    user_record = next(
        (u for u in REGISTERED_USERS if re.sub(r'\D', '', str(u.get('mobile', ''))) == clean_mob and clean_mob),
        None,
    )
    if not user_record and username:
        is_approved = preserve_approved or ADMIN_SETTINGS.get('auto_approval_enabled', True)
        user_record = {
            'id': len(REGISTERED_USERS) + 1,
            'name': username,
            'mobile': mobile,
            'status': 'Approved' if is_approved else 'Pending',
            'registered_at': datetime.now(),
            'approved_at': datetime.now().isoformat() if is_approved else None,
            'last_seen': datetime.now(),
            'is_online': True,
        }
        REGISTERED_USERS.append(user_record)
        save_registered_users()
    return user_record


def touch_user_online(mobile_or_name=None):
    now = datetime.now()
    user_auth = get_user_auth() or {}
    target_mobile = re.sub(r'\D', '', str(mobile_or_name or user_auth.get('mobile', '')))
    target_name = str(mobile_or_name or user_auth.get('username', '')).strip().lower()
    changed = False
    for u in REGISTERED_USERS:
        u_mob = re.sub(r'\D', '', str(u.get('mobile', '')))
        u_name = str(u.get('name', '')).strip().lower()
        if (target_mobile and u_mob == target_mobile) or (target_name and u_name == target_name):
            u['last_seen'] = now
            u['is_online'] = True
            u['online_status'] = 'Online'
            changed = True
        else:
            last_seen = u.get('last_seen')
            is_on = bool(isinstance(last_seen, datetime) and (now - last_seen) < timedelta(minutes=5))
            u['is_online'] = is_on
            u['online_status'] = 'Online' if is_on else 'Offline'
    if changed:
        save_registered_users()
    return REGISTERED_USERS


def refresh_all_users_online_status():
    now = datetime.now()
    for u in REGISTERED_USERS:
        last_seen = u.get('last_seen')
        is_on = bool(isinstance(last_seen, datetime) and (now - last_seen) < timedelta(minutes=5))
        u['is_online'] = is_on
        u['online_status'] = 'Online' if is_on else 'Offline'
    return REGISTERED_USERS


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

PENDING_OTPS = {}


def _normalize_chat_message(msg):
    if not isinstance(msg, dict):
        return {
            'id': 0,
            'username': 'biju',
            'user': 'biju',
            'sender': 'biju',
            'role': 'user',
            'mobile': '',
            'message': str(msg),
            'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
        }
    name = (
        msg.get('username')
        or msg.get('user')
        or msg.get('sender')
        or ('Admin - Bijoosh Padmakumar' if msg.get('role') == 'admin' else 'biju')
    )
    name = str(name).strip() or 'biju'
    text = str(msg.get('message') or msg.get('text') or '').strip()
    ts = str(msg.get('timestamp') or datetime.now().strftime('%b %d, %Y, %I:%M %p')).strip()
    return {
        'id': msg.get('id', 0),
        'username': name,
        'user': name,
        'sender': name,
        'role': msg.get('role', 'user'),
        'mobile': str(msg.get('mobile') or ''),
        'message': text,
        'timestamp': ts,
    }


def load_chat_messages():
    try:
        if os.path.exists(CHAT_FILE):
            with open(CHAT_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                if isinstance(raw, list):
                    return [_normalize_chat_message(m) for m in raw]
    except Exception as e:
        print(f'Error loading chat messages: {e}')
    return []


def save_chat_messages(messages):
    try:
        normalized = [_normalize_chat_message(m) for m in messages[-500:]]
        with open(CHAT_FILE, 'w', encoding='utf-8') as f:
            json.dump(normalized, f, indent=2)
    except Exception as e:
        print(f'Error saving chat messages: {e}')


CHAT_MESSAGES = load_chat_messages()


def check_user_validity(user):
    if not ADMIN_SETTINGS.get('auto_approval_enabled', True):
        return
    now = datetime.now()
    if user['status'] == 'Pending':
        reg_time = user.get('registered_at', now)
        if isinstance(reg_time, str):
            try:
                reg_time = datetime.fromisoformat(reg_time)
            except Exception:
                reg_time = now
        if now - reg_time > timedelta(minutes=5):
            user['status'] = 'Approved'
            user['approved_at'] = now.isoformat()
            save_registered_users()

    if user['status'] == 'Approved' and user.get('approved_at'):
        try:
            approved_date = datetime.fromisoformat(user['approved_at'])
            if now - approved_date > timedelta(days=30):
                user['status'] = 'Pending'
                user['approved_at'] = None
                user['registered_at'] = now
                save_registered_users()
        except Exception:
            pass


def get_festival_greeting():
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    m = ist_now.month
    d = ist_now.day
    y = ist_now.year

    festivals_by_date = {
        (2026, 1, 1): 'Happy New Year',
        (2026, 1, 14): 'Happy Makar Sankranti / Pongal',
        (2026, 1, 26): 'Happy Republic Day',
        (2026, 2, 15): 'Happy Maha Shivaratri',
        (2026, 3, 4): 'Happy Holi',
        (2026, 3, 19): 'Happy Ugadi / Gudi Padwa',
        (2026, 3, 26): 'Happy Rama Navami',
        (2026, 3, 31): 'Happy Mahavir Jayanti',
        (2026, 4, 3): 'Happy Good Friday',
        (2026, 4, 14): 'Happy Vishu',
        (2026, 5, 1): 'Happy Buddha Purnima',
        (2026, 8, 15): 'Happy Independence Day',
        (2026, 8, 28): 'Happy Raksha Bandhan',
        (2026, 9, 4): 'Happy Krishna Janmashtami',
        (2026, 9, 14): 'Happy Ganesh Chaturthi',
        (2026, 10, 2): 'Happy Mahatma Gandhi Jayanti',
        (2026, 10, 20): 'Happy Dussehra',
        (2026, 11, 8): 'Happy Diwali',
        (2026, 11, 24): 'Happy Guru Nanak Jayanti',
        (2026, 12, 25): 'Merry Christmas',
    }

    recurring_festivals = {
        (1, 1): 'Happy New Year',
        (1, 26): 'Happy Republic Day',
        (8, 15): 'Happy Independence Day',
        (12, 25): 'Merry Christmas',
    }

    return festivals_by_date.get((y, m, d), recurring_festivals.get((m, d), None))


WHATSAPP_LOGS = []


def _dispatch_whatsapp_sync(message, to_phone=None):
    target_phone = (
        to_phone
        or os.getenv('WHATSAPP_TO')
        or os.getenv('ADMIN_WHATSAPP')
        or os.getenv('CALLMEBOT_PHONE')
        or ADMIN_MOBILE
    ).strip()
    clean_digits = re.sub(r'\D', '', target_phone)
    if len(clean_digits) == 10:
        clean_digits = '91' + clean_digits

    now_str = datetime.now().strftime('%b %d, %Y, %I:%M:%S %p')

    callmebot_key = (
        os.getenv('CALLMEBOT_APIKEY')
        or os.getenv('CALLMEBOT_API_KEY')
        or os.getenv('WHATSAPP_API_KEY')
        or ''
    ).strip()
    callmebot_phone = re.sub(r'\D', '', os.getenv('CALLMEBOT_PHONE') or clean_digits)
    if len(callmebot_phone) == 10:
        callmebot_phone = '91' + callmebot_phone

    if callmebot_key and callmebot_phone:
        try:
            resp = requests.get(
                'https://api.callmebot.com/whatsapp.php',
                params={'phone': callmebot_phone, 'text': message, 'apikey': callmebot_key},
                timeout=15,
            )
            WHATSAPP_LOGS.append({'time': now_str, 'provider': 'callmebot', 'status': resp.status_code, 'message': message})
            if resp.status_code in (200, 201):
                return True
        except Exception as e:
            WHATSAPP_LOGS.append({'time': now_str, 'provider': 'callmebot', 'status': f'error: {e}', 'message': message})

    wa_token = os.getenv('WHATSAPP_TOKEN', '').strip()
    wa_phone_id = os.getenv('WHATSAPP_PHONE_ID', '').strip()
    if wa_token and wa_phone_id and clean_digits:
        try:
            resp = requests.post(
                f'https://graph.facebook.com/v20.0/{wa_phone_id}/messages',
                headers={
                    'Authorization': f'Bearer {wa_token}',
                    'Content-Type': 'application/json',
                },
                json={
                    'messaging_product': 'whatsapp',
                    'to': clean_digits,
                    'type': 'text',
                    'text': {'body': message},
                },
                timeout=15,
            )
            WHATSAPP_LOGS.append({'time': now_str, 'provider': 'meta_cloud', 'status': resp.status_code, 'message': message})
            if resp.status_code in (200, 201):
                return True
        except Exception as e:
            WHATSAPP_LOGS.append({'time': now_str, 'provider': 'meta_cloud', 'status': f'error: {e}', 'message': message})

    tw_sid = os.getenv('TWILIO_ACCOUNT_SID', '').strip()
    tw_token = os.getenv('TWILIO_AUTH_TOKEN', '').strip()
    tw_from = os.getenv('TWILIO_WHATSAPP_FROM', '').strip()
    tw_to = (os.getenv('TWILIO_WHATSAPP_TO') or f'whatsapp:+{clean_digits}').strip()
    if tw_sid and tw_token and tw_from and tw_to:
        try:
            resp = requests.post(
                f'https://api.twilio.com/2010-04-01/Accounts/{tw_sid}/Messages.json',
                auth=(tw_sid, tw_token),
                data={'From': tw_from, 'To': tw_to, 'Body': message},
                timeout=15,
            )
            WHATSAPP_LOGS.append({'time': now_str, 'provider': 'twilio', 'status': resp.status_code, 'message': message})
            if resp.status_code in (200, 201):
                return True
        except Exception as e:
            WHATSAPP_LOGS.append({'time': now_str, 'provider': 'twilio', 'status': f'error: {e}', 'message': message})

    WHATSAPP_LOGS.append({'time': now_str, 'provider': 'unconfigured', 'status': 'skipped', 'message': message})
    return False


def send_whatsapp_notification(message, to_phone=None):
    threading.Thread(target=_dispatch_whatsapp_sync, args=(message, to_phone), daemon=True).start()
    return True


def send_email_notification(subject, body):
    sender_email = os.getenv('MAIL_USERNAME', ADMIN_EMAIL)
    sender_password = os.getenv('MAIL_PASSWORD', '')
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
        print(f'Failed to send email: {e}')


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
                send_whatsapp_notification("Reminder: Upload Today's Latest NAV Data on the Admin Portal.")
                last_8am_sent = current_date

            if current_hour == 22 and current_minute == 0 and last_10pm_sent != current_date:
                user_summary = 'Here is the daily summary of registered users and their details:\n\n'
                for u in REGISTERED_USERS:
                    user_summary += f"- Name: {u['name']} | Mobile: {u['mobile']} | Status: {u['status']}\n"
                send_email_notification('Daily User Details Report (10:00 PM)', user_summary)
                send_whatsapp_notification(user_summary)
                last_10pm_sent = current_date
        except Exception as e:
            print(f'Scheduler error: {e}')

        time.sleep(30)


threading.Thread(target=daily_scheduler, daemon=True).start()

CACHE_FILE = 'market_cache.json'

DEFAULT_MARKET_CACHE = {
    'nifty50': {'value': '25,387.40', 'change': '+132.35 pts (+0.52%)', 'is_positive': True},
    'sensex': {'value': '82,532.19', 'change': '+427.40 pts (+0.52%)', 'is_positive': True},
    'nifty500': {'value': '23,822.30', 'change': '+42.00 pts (+0.18%)', 'is_positive': True},
    'trend_data': [
        {'date': '09 Nov', 'sensex': '81,106.65', 'change': 0.0},
        {'date': '11 Nov', 'sensex': '81,879.40', 'change': 772.75},
        {'date': '12 Nov', 'sensex': '81,911.01', 'change': 31.61},
        {'date': '13 Nov', 'sensex': '81,592.45', 'change': -318.56},
        {'date': '16 Nov', 'sensex': '82,104.79', 'change': 512.34},
    ],
}

CHART_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json',
}


def load_market_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return json.loads(json.dumps(DEFAULT_MARKET_CACHE))


def save_market_cache(cache_data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)
    except Exception:
        pass


if not os.path.exists(CACHE_FILE):
    save_market_cache(DEFAULT_MARKET_CACHE)


def fetch_yahoo_chart_series(symbol, range_str='20d'):
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    for host in ('query1.finance.yahoo.com', 'query2.finance.yahoo.com'):
        try:
            url = f'https://{host}/v8/finance/chart/{symbol}'
            resp = requests.get(
                url,
                params={'interval': '1d', 'range': range_str},
                headers=CHART_HEADERS,
                timeout=8,
            )
            if resp.status_code == 200:
                payload = resp.json()
                res_list = payload.get('chart', {}).get('result') or []
                if res_list:
                    res = res_list[0]
                    meta = res.get('meta', {})
                    timestamps = res.get('timestamp') or []
                    closes = (
                        res.get('indicators', {})
                        .get('quote', [{}])[0]
                        .get('close', [])
                    )
                    points = []
                    for ts, cl in zip(timestamps, closes):
                        if cl is not None:
                            dt = datetime.fromtimestamp(ts, tz=ist_tz)
                            points.append((dt, float(cl)))
                    if points:
                        return meta, points
        except Exception as e:
            print(f'Yahoo chart fetch failed for {symbol} on {host}: {e}')
    return None, []


def get_live_market_data():
    cache = load_market_cache()
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    today_date = ist_now.date()

    is_weekend = ist_now.weekday() >= 5
    is_market_hours = (not is_weekend) and (
        9 <= ist_now.hour < 16 or (ist_now.hour == 16 and ist_now.minute == 0)
    )

    indices = {
        'nifty50': '%5ENSEI',
        'sensex': '%5EBSESN',
        'nifty500': '%5ECRSLDX',
    }

    result = {}
    sensex_points = []

    for key, symbol in indices.items():
        meta, points = fetch_yahoo_chart_series(symbol, '20d')
        if not points:
            try:
                yf_sym = symbol.replace('%5E', '^')
                t_obj = yf.Ticker(yf_sym)
                hist = t_obj.history(period='20d', interval='1d')
                if hist is not None and not hist.empty:
                    ist_tz = timezone(timedelta(hours=5, minutes=30))
                    points = [
                        (idx.to_pydatetime().astimezone(ist_tz), float(row['Close']))
                        for idx, row in hist.iterrows()
                        if pd.notna(row.get('Close'))
                    ]
            except Exception as e:
                print(f'yfinance fallback error for {key}: {e}')

        if key == 'sensex' and points:
            sensex_points = points

        if points:
            completed = [p for p in points if p[0].date() < today_date]
            ltp = meta.get('regularMarketPrice') if meta else None
            if ltp is None:
                ltp = points[-1][1]
            ltp = float(ltp)

            if completed:
                prev_close = completed[-1][1]
            elif len(points) >= 2:
                prev_close = points[-2][1]
            else:
                prev_close = ltp

            change = ltp - prev_close
            pct_change = (change / prev_close) * 100 if prev_close else 0.0
            result[key] = {
                'value': f'{ltp:,.2f}',
                'change': f'{change:+,.2f} pts ({pct_change:+.2f}%)',
                'is_positive': change >= 0,
            }
        else:
            cached_item = cache.get(key, DEFAULT_MARKET_CACHE[key])
            result[key] = {
                'value': cached_item.get('value', '0.00'),
                'change': cached_item.get('change', '+0.00 pts (0.00%)'),
                'is_positive': cached_item.get('is_positive', True),
            }

    trend_data = []
    if sensex_points and len(sensex_points) >= 2:
        completed = [p for p in sensex_points if p[0].date() < today_date]
        if len(completed) < 5:
            completed = sensex_points[:-1] if len(sensex_points) > 1 else sensex_points
        last5 = completed[-5:]
        prev_val = None
        for idx_i, (dt_obj, close_val) in enumerate(last5):
            dt_str = dt_obj.strftime('%d %b')
            chg = round(close_val - prev_val, 2) if (prev_val is not None and idx_i > 0) else 0.0
            prev_val = close_val
            trend_data.append({
                'date': dt_str,
                'sensex': f'{close_val:,.2f}',
                'change': chg,
            })

    if not trend_data:
        trend_data = cache.get('trend_data') or DEFAULT_MARKET_CACHE['trend_data']

    if result.get('sensex', {}).get('value') not in (None, '0.00'):
        save_market_cache({
            'nifty50': result['nifty50'],
            'sensex': result['sensex'],
            'nifty500': result['nifty500'],
            'trend_data': trend_data,
        })

    if not is_market_hours:
        time_label = f"CLOSED | As on 04:00 PM | {ist_now.strftime('%d %b %Y')}"
    else:
        time_label = f"Live as of: {ist_now.strftime('%b %d, %Y, %I:%M:%S %p')}"

    return {
        'nifty50': result['nifty50'],
        'sensex': result['sensex'],
        'nifty500': result['nifty500'],
        'time_label': time_label,
        'is_market_open': is_market_hours,
    }, trend_data


@app.route('/api/market-live')
@limiter.exempt
def market_live():
    market_info, market_trend = get_live_market_data()
    payload = dict(market_info)
    payload['trend_data'] = market_trend
    return jsonify(payload)


@app.route('/api/market-sync', methods=['GET', 'POST'])
@limiter.exempt
def market_sync():
    data = request.get_json(silent=True) or {}
    if data and data.get('sensex') and data.get('nifty50'):
        save_market_cache({
            'nifty50': data.get('nifty50'),
            'sensex': data.get('sensex'),
            'nifty500': data.get('nifty500'),
            'trend_data': data.get('trend_data') or load_market_cache().get('trend_data'),
        })
    return jsonify({'success': True})


@app.route('/api/get-messages', methods=['GET'])
def get_messages():
    normalized = [_normalize_chat_message(m) for m in CHAT_MESSAGES]
    return jsonify({'success': True, 'messages': normalized})


@app.route('/api/send-message', methods=['POST'])
def send_message():
    data = request.get_json(silent=True) or request.form or {}
    text = str(data.get('message') or data.get('text') or '').strip()
    if not text:
        return jsonify({'success': False, 'message': 'Message cannot be empty.'}), 400

    portal_role = str(
        data.get('role')
        or request.headers.get('X-Portal-Role')
        or ('admin' if str(data.get('username', '')).startswith('Admin') else 'user')
    ).strip().lower()

    if portal_role == 'admin':
        if not is_admin_authenticated():
            return jsonify({'success': False, 'message': 'Admin session expired. Please log in again.'}), 401
        sender_name = 'Admin - Bijoosh Padmakumar'
        role = 'admin'
        mobile = ADMIN_MOBILE
        ADMIN_ACTIVITY['last_active'] = datetime.now()
    else:
        user_auth = get_user_auth()
        if not user_auth:
            return jsonify({'success': False, 'message': 'User session expired. Please log in again.'}), 401
        sender_name = str(user_auth.get('username') or data.get('username') or 'Client').strip()
        role = 'user'
        mobile = str(user_auth.get('mobile') or data.get('mobile') or '').strip()
        ensure_user_record(sender_name, mobile, preserve_approved=True)
        touch_user_online(mobile)

    entry = _normalize_chat_message({
        'id': len(CHAT_MESSAGES) + 1,
        'username': sender_name,
        'user': sender_name,
        'sender': sender_name,
        'role': role,
        'mobile': mobile,
        'message': text,
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    })
    CHAT_MESSAGES.append(entry)
    save_chat_messages(CHAT_MESSAGES)

    if role == 'user':
        send_whatsapp_notification(f'User Message from {sender_name} ({mobile}): {text}')

    return jsonify({
        'success': True,
        'message': 'Message sent.',
        'data': entry,
        'messages': CHAT_MESSAGES,
    })


def format_pct(val):
    try:
        return round(float(val) * 100, 2)
    except Exception:
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
        'october': 'October', 'november': 'November', 'december': 'December',
    }
    for k, v in month_map.items():
        if k in fn:
            month = v
            break
    return year, month


@app.route('/')
def home():
    if get_user_auth():
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))


@app.route('/health')
def health_check():
    return 'OK', 200


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('20 per minute')
def login():
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
            if (mobile in PENDING_OTPS and PENDING_OTPS[mobile] == entered_code) or (display_code and entered_code == display_code):
                PENDING_OTPS.pop(mobile, None)
                login_ts = datetime.now().isoformat()
                session.permanent = True
                session['user_username'] = username
                session['user_mobile'] = mobile
                session['user_login_ts'] = login_ts

                user_record = next((u for u in REGISTERED_USERS if re.sub(r'\D', '', u['mobile']) == clean_mobile), None)
                if not user_record:
                    user_record = {
                        'id': len(REGISTERED_USERS) + 1,
                        'name': username,
                        'mobile': mobile,
                        'status': 'Approved' if ADMIN_SETTINGS.get('auto_approval_enabled', True) else 'Pending',
                        'registered_at': datetime.now(),
                        'approved_at': datetime.now().isoformat() if ADMIN_SETTINGS.get('auto_approval_enabled', True) else None,
                        'last_seen': datetime.now(),
                        'is_online': True,
                    }
                    REGISTERED_USERS.append(user_record)
                    save_registered_users()
                    send_whatsapp_notification(f'New User Login/Approval Request: {username} ({mobile})')
                else:
                    user_record['name'] = username
                    check_user_validity(user_record)
                    save_registered_users()
                touch_user_online(mobile)
                resp = redirect(url_for('pending_approval') if user_record['status'] == 'Pending' else url_for('user_dashboard'))
                return set_user_cookie(resp, username, mobile, login_ts)
            else:
                flash('Invalid code entered. Please type the correct displayed code.', 'danger')
                return render_template('login.html', step='verify_code', username=username, mobile=mobile, display_code=display_code)

    return render_template('login.html', step='request_code', display_code='')


@app.route('/pending-approval')
def pending_approval():
    user_auth = get_user_auth()
    if not user_auth:
        return redirect(url_for('login'))
    mobile = user_auth.get('mobile', '')
    clean_mob = re.sub(r'\D', '', mobile)
    user_record = next((u for u in REGISTERED_USERS if re.sub(r'\D', '', u['mobile']) == clean_mob), None)
    if user_record:
        check_user_validity(user_record)
        if user_record['status'] == 'Approved':
            return redirect(url_for('user_dashboard'))
    return render_template('pending_approval.html', username=user_auth.get('username', 'User'))


@app.route('/user-dashboard')
def user_dashboard():
    user_auth = get_user_auth()
    if not user_auth:
        return redirect(url_for('login'))

    username = user_auth.get('username', 'Client')
    mobile = user_auth.get('mobile', '')

    user_record = ensure_user_record(username, mobile, preserve_approved=True)
    touch_user_online(mobile)
    refresh_all_users_online_status()

    if user_record:
        check_user_validity(user_record)
        if user_record['status'] == 'Pending':
            return redirect(url_for('pending_approval'))

    remaining_days = 30
    try:
        login_ts_raw = user_auth.get('login_ts')
        if login_ts_raw:
            login_dt = datetime.fromisoformat(login_ts_raw)
            elapsed_days = (datetime.now() - login_dt).days
            remaining_days = max(0, 30 - elapsed_days)
    except Exception:
        remaining_days = 30

    try:
        market_info, market_trend_data = get_live_market_data()
    except Exception:
        cache = load_market_cache()
        market_info = {
            'nifty50': cache['nifty50'],
            'sensex': cache['sensex'],
            'nifty500': cache['nifty500'],
            'time_label': 'Cached Market Data',
            'is_market_open': False,
        }
        market_trend_data = cache.get('trend_data', [])

    admin_online = (datetime.now() - ADMIN_ACTIVITY['last_active']) < timedelta(minutes=5)
    festival_greeting = get_festival_greeting()

    latest_data_updated = False
    latest_filename = 'latest_nav.jpg'
    try:
        meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as mf:
                meta = json.load(mf)
                latest_filename = meta.get('filename', 'latest_nav.jpg')
                last_time = meta.get('upload_time', '')
                if is_today_filename(latest_filename, last_time):
                    latest_data_updated = True
    except Exception as e:
        print(f'Error checking upload status: {e}')

    user_requests = [r for r in DOWNLOAD_REQUESTS if r.get('username', '').lower() == username.lower()]

    return render_template(
        'user_dashboard.html',
        username=username,
        mobile=mobile,
        remaining_days=remaining_days,
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
        messages=CHAT_MESSAGES,
    )


@app.route('/api/user-state')
@limiter.exempt
def api_user_state():
    user_auth = get_user_auth()
    if not user_auth:
        return jsonify({'success': False, 'message': 'Session expired.'}), 401
    username = user_auth.get('username', 'Client')
    touch_user_online(user_auth.get('mobile'))
    user_requests = [r for r in DOWNLOAD_REQUESTS if r.get('username', '').lower() == username.lower()]
    admin_online = (datetime.now() - ADMIN_ACTIVITY['last_active']) < timedelta(minutes=5)
    return jsonify({
        'success': True,
        'download_requests': user_requests,
        'admin_online': admin_online,
    })


@app.route('/request-download', methods=['POST'])
def request_download():
    user_auth = get_user_auth()
    if not user_auth:
        return jsonify({'success': False, 'message': 'Session expired. Please log in again.'}), 401
    data = request.get_json(silent=True) or {}
    file_name = data.get('filename', 'latest_nav.jpg')
    download_type = data.get('type', 'download')
    username = user_auth.get('username', 'Client')

    req_id = len(DOWNLOAD_REQUESTS) + 1
    entry = {
        'id': req_id,
        'username': username,
        'filename': file_name,
        'type': download_type,
        'status': 'Pending',
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    }
    DOWNLOAD_REQUESTS.append(entry)
    save_download_requests()
    touch_user_online(user_auth.get('mobile'))
    send_whatsapp_notification(f'Download Request from {username}: {file_name} ({download_type})')
    return jsonify({
        'success': True,
        'message': 'Approval request sent to Admin successfully.',
        'request': entry,
    })


@app.route('/get-nav-image-base64/<path:filename>')
def get_nav_image_base64(filename):
    if not get_user_auth() and not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(target_path):
        for root, _, files in os.walk(ARCHIVE_FOLDER):
            if filename in files:
                target_path = os.path.join(root, filename)
                break

    if os.path.exists(target_path):
        with open(target_path, 'rb') as img_f:
            b64_data = base64.b64encode(img_f.read()).decode('utf-8')
        return jsonify({'success': True, 'image_data': f'data:image/jpeg;base64,{b64_data}'})

    return jsonify({'success': False, 'message': 'Image not found'})


@app.route('/view-archive-secured/<path:filename>')
def view_archive_secured(filename):
    portal_role = request.args.get('role', '').strip().lower()
    user_auth = get_user_auth()

    if portal_role == 'admin':
        if not is_admin_authenticated():
            return redirect(url_for('admin_login'))
        for root, _, files in os.walk(ARCHIVE_FOLDER):
            if filename in files:
                return send_from_directory(root, filename)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    if not user_auth and not is_admin_authenticated():
        return redirect(url_for('login'))

    if is_admin_authenticated() and not user_auth:
        for root, _, files in os.walk(ARCHIVE_FOLDER):
            if filename in files:
                return send_from_directory(root, filename)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    username = (user_auth or {}).get('username', '')
    approved_req = next(
        (
            r for r in DOWNLOAD_REQUESTS
            if r.get('username', '').lower() == username.lower()
            and r['filename'] == filename
            and r['status'] == 'Approved'
            and r['type'] == 'download'
        ),
        None,
    )
    if approved_req:
        for root, _, files in os.walk(ARCHIVE_FOLDER):
            if filename in files:
                return send_from_directory(root, filename)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    flash('Download requires Admin Approval. Request submitted.', 'warning')
    return redirect(url_for('user_dashboard'))


@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    user_auth = get_user_auth()
    if not user_auth:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Session expired. Please log in again.'}), 401
        return redirect(url_for('login'))

    data = request.get_json(silent=True) or request.form or {}
    feedback_text = str(data.get('feedback') or '').strip()
    rating = str(data.get('rating') or '5').strip()

    if not feedback_text:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Feedback cannot be empty.'}), 400
        return redirect(url_for('user_dashboard'))

    entry = {
        'id': len(USER_FEEDBACKS) + 1,
        'username': user_auth.get('username', 'Client'),
        'feedback': feedback_text,
        'rating': int(rating) if rating.isdigit() else 5,
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    }
    USER_FEEDBACKS.append(entry)
    touch_user_online(user_auth.get('mobile'))

    if request.is_json:
        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully!',
            'feedback': entry,
        })

    flash('Feedback submitted successfully!', 'success')
    return redirect(url_for('user_dashboard'))


@app.route('/admin-login', methods=['GET', 'POST'])
@limiter.limit('20 per minute')
def admin_login():
    if request.method == 'POST':
        mobile_input = request.form.get('mobile')
        password_input = request.form.get('password')
        if mobile_input == '+918078535666' and password_input == 'Bichu@5419':
            session.permanent = True
            session['admin_authenticated'] = True
            ADMIN_ACTIVITY['last_active'] = datetime.now()
            resp = redirect(url_for('admin_dashboard'))
            return set_admin_cookie(resp)
        else:
            flash('Invalid Admin Credentials', 'danger')
    return render_template('admin_login.html')


@app.route('/admin')
def admin_redirect():
    if is_admin_authenticated():
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))


@app.route('/admin-dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not is_admin_authenticated():
        return redirect(url_for('admin_login'))

    ADMIN_ACTIVITY['last_active'] = datetime.now()
    refresh_all_users_online_status()

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
        messages=[_normalize_chat_message(m) for m in CHAT_MESSAGES],
    )


@app.route('/api/admin-state')
@limiter.exempt
def api_admin_state():
    if not is_admin_authenticated():
        return jsonify({'success': False}), 401
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    refresh_all_users_online_status()
    users_payload = []
    for u in REGISTERED_USERS:
        last_seen = u.get('last_seen')
        last_seen_str = last_seen.strftime('%b %d, %Y, %I:%M %p') if isinstance(last_seen, datetime) else (u.get('last_login') or 'N/A')
        users_payload.append({
            'id': u['id'],
            'name': u['name'],
            'mobile': u['mobile'],
            'is_online': bool(u.get('is_online')),
            'last_seen': last_seen_str,
            'status': u['status'],
        })
    return jsonify({
        'success': True,
        'users': users_payload,
        'download_requests': DOWNLOAD_REQUESTS,
        'feedbacks': USER_FEEDBACKS,
        'auto_approval_enabled': ADMIN_SETTINGS.get('auto_approval_enabled', True),
    })


@app.route('/admin/approve-download/<int:req_id>', methods=['POST'])
def approve_download(req_id):
    if not is_admin_authenticated():
        if request.is_json:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        return redirect(url_for('admin_login'))
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    for req in DOWNLOAD_REQUESTS:
        if req['id'] == req_id:
            req['status'] = 'Approved'
            save_download_requests()
            if not request.is_json:
                flash(f"Download request for {req['filename']} approved!", 'success')
            break
    if request.is_json:
        return jsonify({'success': True})
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reject-download/<int:req_id>', methods=['POST'])
def reject_download(req_id):
    if not is_admin_authenticated():
        if request.is_json:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        return redirect(url_for('admin_login'))
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    for req in DOWNLOAD_REQUESTS:
        if req['id'] == req_id:
            req['status'] = 'Rejected'
            save_download_requests()
            if not request.is_json:
                flash(f"Download request for {req['filename']} rejected.", 'danger')
            break
    if request.is_json:
        return jsonify({'success': True})
    return redirect(url_for('admin_dashboard'))


@app.route('/toggle-auto-approval', methods=['POST'])
def toggle_auto_approval():
    if not is_admin_authenticated():
        if request.is_json:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        return redirect(url_for('admin_login'))
    ADMIN_ACTIVITY['last_active'] = datetime.now()
    ADMIN_SETTINGS['auto_approval_enabled'] = not ADMIN_SETTINGS.get('auto_approval_enabled', True)
    status_text = 'Enabled' if ADMIN_SETTINGS['auto_approval_enabled'] else 'Disabled'
    if request.is_json:
        return jsonify({
            'success': True,
            'auto_approval_enabled': ADMIN_SETTINGS['auto_approval_enabled'],
            'message': f'Auto-approval has been {status_text} successfully!',
        })
    flash(f'Auto-approval has been {status_text} successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/update-user-status/<int:user_id>/<status>', methods=['POST'])
def update_user_status(user_id, status):
    if not is_admin_authenticated():
        if request.is_json:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        return redirect(url_for('admin_login'))

    ADMIN_ACTIVITY['last_active'] = datetime.now()

    for user in REGISTERED_USERS:
        if user['id'] == user_id:
            user['status'] = status.capitalize()
            if status.capitalize() == 'Approved':
                user['approved_at'] = datetime.now().isoformat()
            else:
                user['approved_at'] = None
            save_registered_users()
            break
    if request.is_json:
        return jsonify({'success': True})
    return redirect(url_for('admin_dashboard'))


@app.route('/approve-all-users', methods=['POST'])
def approve_all_users():
    if not is_admin_authenticated():
        if request.is_json:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        return redirect(url_for('admin_login'))

    ADMIN_ACTIVITY['last_active'] = datetime.now()
    now_iso = datetime.now().isoformat()
    for user in REGISTERED_USERS:
        if user['status'] == 'Pending':
            user['status'] = 'Approved'
            user['approved_at'] = now_iso
    save_registered_users()
    if request.is_json:
        return jsonify({'success': True, 'message': 'All pending users approved successfully!'})
    flash('All pending users approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/decline-all-users', methods=['POST'])
def decline_all_users():
    if not is_admin_authenticated():
        if request.is_json:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        return redirect(url_for('admin_login'))

    ADMIN_ACTIVITY['last_active'] = datetime.now()
    for user in REGISTERED_USERS:
        if user['status'] == 'Pending':
            user['status'] = 'Pending'
            user['approved_at'] = None
    save_registered_users()
    if request.is_json:
        return jsonify({'success': True, 'message': 'All pending users declined successfully!'})
    flash('All pending users declined successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


def format_alloc(val):
    try:
        return f'{round(float(val) * 100, 2)}%'
    except Exception:
        return str(val).strip()


def match_fund_name(sheet_name, fund_names):
    s_clean = sheet_name.strip().lower()
    for fn in fund_names:
        if fn.lower() == s_clean:
            return fn
    s_norm = ''.join(ch for ch in s_clean if ch.isalnum())
    for fn in fund_names:
        if ''.join(ch for ch in fn.lower() if ch.isalnum()) == s_norm:
            return fn
    if len(s_clean) >= 28:
        for fn in fund_names:
            if fn.lower().startswith(s_clean[:28]):
                return fn
    return sheet_name.strip()


def parse_workbook(excel_source):
    xl = pd.ExcelFile(excel_source)
    summary_df = xl.parse(xl.sheet_names[0])
    summary_df = summary_df.dropna(subset=[summary_df.columns[0]])
    fund_names = [
        str(x).strip()
        for x in summary_df.iloc[:, 0]
        if str(x).strip() and str(x).strip().lower() not in ('nan', 'funds')
    ]

    sectors_rows, holdings_rows, debt_rows = [], [], []

    for sheet_name in xl.sheet_names[1:]:
        df = xl.parse(sheet_name)
        if df.empty or df.shape[1] < 2:
            continue

        matched_name = match_fund_name(sheet_name, fund_names)
        current_section = None

        for _, row in df.iterrows():
            col0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
            col1 = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
            if not col0:
                continue

            col0_low = col0.lower()
            if col0_low.startswith('top 10 sectors'):
                current_section = 'sectors'
                continue
            if col0_low == 'equity':
                current_section = 'equity'
                continue
            if col0_low == 'corporate securities':
                current_section = 'corp_debt'
                continue
            if col0_low.startswith('government securities'):
                current_section = 'gov_debt'
                continue
            if col0_low == 'debt portfolio by maturity':
                current_section = 'maturity'
                continue
            if col0_low == 'rating profile':
                current_section = 'rating'
                continue
            if col0_low.startswith('holdings as on'):
                current_section = None
                continue
            if col0_low in ('total', 'grand total', 'others: debt, money-market, current assets and cash'):
                continue

            if current_section == 'sectors' and col1 and col1.lower() not in ('% of assets invested', 'nan'):
                sectors_rows.append({
                    'fund': matched_name,
                    'sector': col0,
                    'allocation': format_alloc(row.iloc[1]),
                })
            elif current_section == 'equity' and col1 and col1.lower() not in ('% of assets invested', 'nan'):
                holdings_rows.append({
                    'fund': matched_name,
                    'asset_type': 'Equity',
                    'holding': col0,
                    'rating': '',
                    'allocation': format_alloc(row.iloc[1]),
                })
            elif current_section == 'corp_debt' and col1 and col1.lower() not in ('rating', 'nan'):
                alloc_raw = row.iloc[2] if df.shape[1] > 2 and pd.notna(row.iloc[2]) else row.iloc[1]
                holdings_rows.append({
                    'fund': matched_name,
                    'asset_type': 'Corporate Debt',
                    'holding': col0,
                    'rating': col1,
                    'allocation': format_alloc(alloc_raw),
                })
            elif current_section == 'gov_debt' and col1 and col1.lower() not in ('rating', 'nan'):
                alloc_raw = row.iloc[2] if df.shape[1] > 2 and pd.notna(row.iloc[2]) else row.iloc[1]
                holdings_rows.append({
                    'fund': matched_name,
                    'asset_type': 'Government Securities',
                    'holding': col0,
                    'rating': col1,
                    'allocation': format_alloc(alloc_raw),
                })
            elif current_section in ('maturity', 'rating') and col1 and col1.lower() not in ('allocation as a %', '% of assets invested', 'nan'):
                debt_rows.append({
                    'fund': matched_name,
                    'metric_type': current_section,
                    'label': col0,
                    'allocation': format_alloc(row.iloc[1]),
                })

    return (
        summary_df,
        pd.DataFrame(sectors_rows),
        pd.DataFrame(holdings_rows),
        pd.DataFrame(debt_rows),
    )


def get_fund_portfolio_details(category, fund_name):
    sectors, holdings, debt_metrics = [], [], []
    if not engine:
        return sectors, holdings, debt_metrics
    target = fund_name.strip().lower()
    try:
        df_s = pd.read_sql(f'SELECT * FROM {category}_sectors', engine)
        if not df_s.empty and 'fund' in df_s.columns:
            matched = df_s[df_s['fund'].astype(str).str.strip().str.lower() == target]
            sectors = matched.to_dict('records')
    except Exception as e:
        print(f'Error reading {category}_sectors: {e}')

    try:
        df_h = pd.read_sql(f'SELECT * FROM {category}_holdings', engine)
        if not df_h.empty and 'fund' in df_h.columns:
            matched = df_h[df_h['fund'].astype(str).str.strip().str.lower() == target]
            holdings = matched.to_dict('records')
    except Exception as e:
        print(f'Error reading {category}_holdings: {e}')

    try:
        df_d = pd.read_sql(f'SELECT * FROM {category}_debt_metrics', engine)
        if not df_d.empty and 'fund' in df_d.columns:
            matched = df_d[df_d['fund'].astype(str).str.strip().str.lower() == target]
            debt_metrics = matched.to_dict('records')
    except Exception as e:
        print(f'Error reading {category}_debt_metrics: {e}')

    return sectors, holdings, debt_metrics


@app.route('/api/fund-portfolio/<category>/<path:fund_name>')
def api_fund_portfolio(category, fund_name):
    if not get_user_auth() and not is_admin_authenticated():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    cat = category.strip().lower()
    if cat not in ('equity', 'balancer', 'debt'):
        return jsonify({'success': False, 'message': 'Invalid category'}), 400
    sectors, holdings, debt_metrics = get_fund_portfolio_details(cat, fund_name)
    return jsonify({
        'success': True,
        'category': cat,
        'fund': fund_name,
        'sectors': sectors,
        'holdings': holdings,
        'debt_metrics': debt_metrics,
    })


def _resolve_fund_viewer_and_back():
    role_hint = (
        request.args.get('role')
        or request.headers.get('X-Portal-Role')
        or ''
    ).strip().lower()
    if role_hint == 'admin' and is_admin_authenticated():
        return True, 'Admin - Bijoosh Padmakumar', url_for('admin_dashboard')
    if role_hint == 'user':
        user_auth = get_user_auth()
        if user_auth:
            touch_user_online(user_auth.get('mobile'))
            return False, user_auth.get('username', 'Client'), url_for('user_dashboard')
    if is_admin_authenticated() and request.referrer and '/admin' in request.referrer:
        return True, 'Admin - Bijoosh Padmakumar', url_for('admin_dashboard')
    user_auth = get_user_auth()
    if user_auth:
        touch_user_online(user_auth.get('mobile'))
        return False, user_auth.get('username', 'Client'), url_for('user_dashboard')
    if is_admin_authenticated():
        return True, 'Admin - Bijoosh Padmakumar', url_for('admin_dashboard')
    return None, None, url_for('login')


@app.route('/fund/<category>/<path:fund_name>')
def fund_detail(category, fund_name):
    active_admin, viewer_label, back_url = _resolve_fund_viewer_and_back()
    if active_admin is None:
        return redirect(url_for('login'))

    cat = category.strip().lower()
    if cat not in ('equity', 'balancer', 'debt'):
        flash('Invalid fund category.', 'danger')
        return redirect(back_url)

    funds = parse_fund_excel_from_db(f'{cat}_funds')
    matched_fund = next((f for f in funds if f['fund'].strip().lower() == fund_name.strip().lower()), None)
    if not matched_fund:
        flash('Fund details not found.', 'warning')
        return redirect(back_url)

    sectors, holdings, debt_metrics = get_fund_portfolio_details(cat, matched_fund['fund'])

    return render_template(
        'fund_detail.html',
        category=cat,
        fund_data=matched_fund,
        sectors=sectors,
        holdings=holdings,
        debt_metrics=debt_metrics,
        viewer_label=viewer_label,
        username=viewer_label,
        back_url=back_url,
    )


@app.route('/admin/fund/<category>/<path:fund_name>')
def admin_fund_detail(category, fund_name):
    if not is_admin_authenticated():
        return redirect(url_for('admin_login'))
    cat = category.strip().lower()
    if cat not in ('equity', 'balancer', 'debt'):
        flash('Invalid fund category.', 'danger')
        return redirect(url_for('admin_dashboard'))
    funds = parse_fund_excel_from_db(f'{cat}_funds')
    matched_fund = next((f for f in funds if f['fund'].strip().lower() == fund_name.strip().lower()), None)
    if not matched_fund:
        flash('Fund details not found.', 'warning')
        return redirect(url_for('admin_dashboard'))
    sectors, holdings, debt_metrics = get_fund_portfolio_details(cat, matched_fund['fund'])
    return render_template(
        'fund_detail.html',
        category=cat,
        fund_data=matched_fund,
        sectors=sectors,
        holdings=holdings,
        debt_metrics=debt_metrics,
        viewer_label='Admin - Bijoosh Padmakumar',
        username='Admin - Bijoosh Padmakumar',
        back_url=url_for('admin_dashboard'),
    )


@app.route('/user/fund/<category>/<path:fund_name>')
def user_fund_detail(category, fund_name):
    user_auth = get_user_auth()
    if not user_auth:
        return redirect(url_for('login'))
    touch_user_online(user_auth.get('mobile'))
    cat = category.strip().lower()
    if cat not in ('equity', 'balancer', 'debt'):
        flash('Invalid fund category.', 'danger')
        return redirect(url_for('user_dashboard'))
    funds = parse_fund_excel_from_db(f'{cat}_funds')
    matched_fund = next((f for f in funds if f['fund'].strip().lower() == fund_name.strip().lower()), None)
    if not matched_fund:
        flash('Fund details not found.', 'warning')
        return redirect(url_for('user_dashboard'))
    sectors, holdings, debt_metrics = get_fund_portfolio_details(cat, matched_fund['fund'])
    viewer_name = user_auth.get('username', 'Client')
    return render_template(
        'fund_detail.html',
        category=cat,
        fund_data=matched_fund,
        sectors=sectors,
        holdings=holdings,
        debt_metrics=debt_metrics,
        viewer_label=viewer_name,
        username=viewer_name,
        back_url=url_for('user_dashboard'),
    )


@app.after_request
def lock_dashboard_fund_links(response):
    try:
        if response.content_type and 'text/html' in response.content_type and response.status_code == 200:
            html = response.get_data(as_text=True)
            if request.path == '/admin-dashboard' and is_admin_authenticated() and '/fund/' in html:
                html = html.replace('href="/fund/', 'href="/admin/fund/')
                html = html.replace("href='/fund/", "href='/admin/fund/")
                response.set_data(html)
            elif request.path == '/user-dashboard' and '/fund/' in html:
                html = html.replace('href="/fund/', 'href="/user/fund/')
                html = html.replace("href='/fund/", "href='/user/fund/")
                response.set_data(html)
    except Exception:
        pass
    return response


@app.route('/upload-master-category', methods=['GET', 'POST'])
def upload_master_category():
    if not is_admin_authenticated():
        return redirect(url_for('admin_login'))

    ADMIN_ACTIVITY['last_active'] = datetime.now()

    if request.method == 'POST':
        try:
            category = request.form.get('category')
            file_key = f'{category}_file'
            if file_key in request.files:
                file = request.files[file_key]
                if file and file.filename != '':
                    if not engine:
                        flash('Database connection error.', 'danger')
                        return redirect(url_for('admin_dashboard'))

                    summary_df, sec_df, hold_df, debt_df = parse_workbook(file)
                    summary_df.to_sql(f'{category}_funds', engine, if_exists='replace', index=False)
                    if not sec_df.empty:
                        sec_df.to_sql(f'{category}_sectors', engine, if_exists='replace', index=False)
                    if not hold_df.empty:
                        hold_df.to_sql(f'{category}_holdings', engine, if_exists='replace', index=False)
                    if not debt_df.empty:
                        debt_df.to_sql(f'{category}_debt_metrics', engine, if_exists='replace', index=False)

                    send_whatsapp_notification(f'{category.capitalize()} Master Excel updated in Supabase!')
                    flash(f'{category.capitalize()} funds, sectors & holdings updated permanently in Supabase!', 'success')
        except Exception as e:
            flash(f'Error updating category: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/upload-nav', methods=['GET', 'POST'])
def upload_nav():
    if not is_admin_authenticated():
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

                file_path_upload = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                latest_ref_path = os.path.join(app.config['UPLOAD_FOLDER'], 'latest_nav.jpg')

                Image.MAX_IMAGE_PIXELS = None
                try:
                    with Image.open(file) as img:
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        img.thumbnail((1200, 1200))
                        img.save(file_path_upload, "JPEG", optimize=True, quality=80)
                        img.save(latest_ref_path, "JPEG", optimize=True, quality=80)
                except Exception as img_err:
                    print(f"Pillow critical error: {img_err}")
                    flash('Failed to process image format. Please upload a standard JPEG/PNG.', 'danger')
                    return redirect(url_for('admin_dashboard'))

                meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
                with open(meta_path, 'w', encoding='utf-8') as mf:
                    json.dump({
                        'filename': filename,
                        'original_filename': raw_fn,
                        'upload_time': datetime.now().isoformat(),
                    }, mf)

                target_year, target_month = extract_date_from_filename(raw_fn)
                archive_target_dir = os.path.join(ARCHIVE_FOLDER, target_year, target_month)
                os.makedirs(archive_target_dir, exist_ok=True)
                archive_file_path = os.path.join(archive_target_dir, filename)
                if os.path.exists(file_path_upload):
                    shutil.copy(file_path_upload, archive_file_path)

                send_whatsapp_notification(f'NAV Published: {filename} (Archived to {target_year}/{target_month})')
                flash(f'Successfully published & optimized NAV: {filename} (Archived to {target_year}/{target_month})', 'success')
            else:
                flash('No file selected for NAV upload.', 'warning')
        except Exception as e:
            flash(f'Error uploading NAV image: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/upload-archive', methods=['GET', 'POST'])
def upload_archive():
    if not is_admin_authenticated():
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
                'oct': 'October', 'nov': 'November', 'dec': 'December',
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
    if not is_admin_authenticated():
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


@app.route('/get-archive-files', methods=['GET'])
def get_archive_files():
    year = request.args.get('year', '').strip()
    month_input = request.args.get('month', '').strip().lower()
    matched_files = []

    month_map = {
        'jan': 'January', 'feb': 'February', 'mar': 'March',
        'apr': 'April', 'may': 'May', 'jun': 'June',
        'jul': 'July', 'aug': 'August', 'sep': 'September',
        'oct': 'October', 'nov': 'November', 'dec': 'December',
        'january': 'January', 'february': 'February', 'march': 'March', 'april': 'April',
        'june': 'June', 'july': 'July', 'august': 'August', 'september': 'September',
        'october': 'October', 'november': 'November', 'december': 'December',
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
