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
        'last_login': 'Nov 06, 2026, 09:45 PM',
    },
    {
        'id': 2,
        'name': 'Priya Nair',
        'mobile': '+91 9876522888',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(days=5),
        'approved_at': datetime.now().isoformat(),
        'last_login': 'Nov 06, 2026, 08:30 PM',
    },
    {
        'id': 3,
        'name': 'biju',
        'mobile': '+917034788666',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(days=10),
        'approved_at': datetime.now().isoformat(),
        'last_login': 'Nov 06, 2026, 10:00 PM',
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

CHAT_MESSAGES = [
    {
        'id': 1,
        'username': 'biju',
        'message': 'Hello Admin, checking connection.',
        'timestamp': 'Nov 06, 2026, 10:00 PM',
        'sender': 'user'
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
    'sensex': {'value': '81,028.02', 'change': '+1,718.02 pts (+2.17%)', 'is_positive': True},
    'nifty500': {'value': '22,769.20', 'change': '+527.80 pts (+2.37%)', 'is_positive': True},
    'trend_data': [
        {'date': '01 Nov', 'sensex': '74,151.04', 'change': 905.01},
        {'date': '02 Nov', 'sensex': '74,459.53', 'change': 308.49},
        {'date': '03 Nov', 'sensex': '76,917.85', 'change': 1225.07},
        {'date': '04 Nov', 'sensex': '77,301.40', 'change': 383.55},
        {'date': '05 Nov', 'sensex': '81,028.02', 'change': 1718.02},
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


def get_live_market_data():
  cache = load_market_cache()
  now_utc = datetime.now(timezone.utc)
  ist_now = now_utc + timedelta(hours=5, minutes=30)
  is_weekend = ist_now.weekday() >= 5
  is_market_hours = (not is_weekend) and (9 <= ist_now.hour < 16 or (ist_now.hour == 16 and ist_now.minute == 0))

  indices = {'nifty50': '^NSEI', 'sensex': '^BSESN', 'nifty500': '^CRSLDX'}
  result = {}
  for key, ticker in indices.items():
    try:
      t_obj = yf.Ticker(ticker)
      todays_data = t_obj.history(period="2d")
      if not todays_data.empty and len(todays_data) >= 1:
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
    sensex_hist = yf.Ticker('^BSESN').history(period="15d")
    if not sensex_hist.empty:
      sensex_hist = sensex_hist.tail(5)
      prev_val = None
      for idx, row in sensex_hist.iterrows():
        dt_str = idx.strftime('%d %b')
        close_val = float(row['Close'])
        chg = round(close_val - prev_val, 2) if prev_val is not None else 0.0
        prev_val = close_val
        trend_data.append({
            'date': dt_str,
            'sensex': f"{close_val:,.2f}",
            'change': chg
        })
  except Exception as e:
    print(f"yfinance trend fetch error: {e}")

  if not trend_data or len(trend_data) < 5:
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
  return jsonify(market_info)


@app.route('/api/messages', methods=['GET'])
def get_messages():
  if 'username' not in session and not session.get('is_admin'):
    return jsonify({'success': False, 'messages': []})
  
  user_filter = session.get('username') if not session.get('is_admin') else request.args.get('user', '')
  if session.get('is_admin') and not user_filter:
    return jsonify({'success': True, 'messages': CHAT_MESSAGES})

  filtered = [m for m in CHAT_MESSAGES if m['username'] == user_filter or session.get('is_admin')]
  return jsonify({'success': True, 'messages': filtered})


@app.route('/api/send-message', methods=['POST'])
def send_message():
  if 'username' not in session and not session.get('is_admin'):
    return jsonify({'success': False, 'message': 'Unauthorized'})
  
  data = request.get_json() or {}
  msg_text = data.get('message', '').strip()
  if not msg_text:
    return jsonify({'success': False, 'message': 'Empty message'})

  now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
  timestamp_str = now_ist.strftime('%b %d, %Y, %I:%M %p')

  username = 'Admin Bijoosh' if session.get('is_admin') else session.get('username', 'Client')
  sender_type = 'admin' if session.get('is_admin') else 'user'

  new_msg = {
      'id': len(CHAT_MESSAGES) + 1,
      'username': username,
      'message': msg_text,
      'timestamp': timestamp_str,
      'sender': sender_type
  }
  CHAT_MESSAGES.append(new_msg)
  return jsonify({'success': True, 'message': 'Message sent successfully.'})


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
              'y4': format_pct(row.iloc[9]) if len(row) > 9 else '0',
              'y5': format_pct(row.iloc[10]) if len(row) > 10 else '0',
              'y7': format_pct(row.iloc[11]) if len(row) > 11 else '0',
              'y10': format_pct(row.iloc[12]) if len(row) > 12 else '0',
              'high': str(row.iloc[13]) if len(row) > 13 else '0',
              'latest': str(row.iloc[14]) if len(row) > 14 else '0',
          })
  except Exception as e:
    print(f'Error reading table {table_name}: {e}')
  return fund_list


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


@app.route('/')
def home():
  return redirect(url_for('login'))


@app.route('/health')
def health_check():
  return 'OK', 200


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
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
      if mobile in PENDING_OTPS and PENDING_OTPS[mobile] == entered_code:
        del PENDING_OTPS[mobile]
        session.permanent = True
        session['username'] = username
        session['mobile'] = mobile
        
        now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        login_time_str = now_ist.strftime('%b %d, %Y, %I:%M %p')

        user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
        if not user_record:
          user_record = {
              'id': len(REGISTERED_USERS) + 1,
              'name': username,
              'mobile': mobile,
              'status': 'Pending',
              'registered_at': datetime.now(),
              'approved_at': None,
              'last_login': login_time_str,
          }
          REGISTERED_USERS.append(user_record)
        else:
          user_record['last_login'] = login_time_str
          check_user_validity(user_record)

        if user_record['status'] == 'Pending':
          return redirect(url_for('pending_approval'))
        return redirect(url_for('user_dashboard'))
      else:
        flash('Invalid code entered. Please type the correct displayed code.', 'danger')
        return render_template('login.html', step='verify_code', username=username, mobile=mobile, display_code=display_code)

  return render_template('login.html', step='request_code', display_code='')


@app.route('/pending-approval')
def pending_approval():
  mobile = session.get('mobile', '')
  user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
  if user_record:
    check_user_validity(user_record)
    if user_record['status'] == 'Approved':
      return redirect(url_for('user_dashboard'))
  return render_template('pending_approval.html', username=session.get('username', 'User'))


@app.route('/user-dashboard')
def user_dashboard():
  try:
    mobile = session.get('mobile', '')
    user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
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


@app.route('/request-download', methods=['POST'])
def request_download():
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
  return jsonify({'success': True, 'message': 'Approval request sent to Admin successfully.'})


@app.route('/get-nav-image-base64/<path:filename>')
def get_nav_image_base64(filename):
  if 'username' not in session and not session.get('is_admin'):
    return jsonify({'success': False, 'message': 'Unauthorized'})
  target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
  if not os.path.exists(target_path):
    for root, dirs, files in os.walk(ARCHIVE_FOLDER):
      if filename in files:
        target_path = os.path.join(root, filename)
        break
  if os.path.exists(target_path):
    import base64
    with open(target_path, 'rb') as img_f:
      b64_data = base64.b64encode(img_f.read()).decode('utf-8')
    return jsonify({'success': True, 'image_data': f"data:image/jpeg;base64,{b64_data}"})
  return jsonify({'success': False, 'message': 'Image not found'})


@app.route('/view-archive-secured/<path:filename>')
def view_archive_secured(filename):
  if 'username' not in session and not session.get('is_admin'):
    return redirect(url_for('login'))
  if session.get('is_admin'):
    for root, dirs, files in os.walk(ARCHIVE_FOLDER):
      if filename in files:
        return send_from_directory(root, filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

  approved_req = next((r for r in DOWNLOAD_REQUESTS if r['username'] == session.get('username') and r['filename'] == filename and r['status'] == 'Approved'), None)
  if approved_req:
    for root, dirs, files in os.walk(ARCHIVE_FOLDER):
      if filename in files:
        return send_from_directory(root, filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
  flash('Download requires Admin Approval.', 'warning')
  return redirect(url_for('user_dashboard'))


@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
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


@app.route('/admin-login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def admin_login():
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


@app.route('/admin')
def admin_redirect():
  if session.get('is_admin'):
    return redirect(url_for('admin_dashboard'))
  return redirect(url_for('admin_login'))


@app.route('/admin-dashboard', methods=['GET', 'POST'])
def admin_dashboard():
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
      chat_messages=CHAT_MESSAGES,
      equity_data=parse_fund_excel_from_db('equity_funds'),
      balancer_data=parse_fund_excel_from_db('balancer_funds'),
      debt_data=parse_fund_excel_from_db('debt_funds'),
      auto_approval_enabled=ADMIN_SETTINGS['auto_approval_enabled'],
      current_time=datetime.now().strftime('%b %d, %Y, %I:%M:%S %p'),
      festival_greeting=festival_greeting,
      user_filter=user_filter,
  )


@app.route('/admin/approve-download/<int:req_id>', methods=['POST'])
def approve_download(req_id):
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  for req in DOWNLOAD_REQUESTS:
    if req['id'] == req_id:
      req['status'] = 'Approved'
      flash(f"Download request approved!", 'success')
      break
  return redirect(url_for('admin_dashboard'))


@app.route('/admin/reject-download/<int:req_id>', methods=['POST'])
def reject_download(req_id):
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  for req in DOWNLOAD_REQUESTS:
    if req['id'] == req_id:
      req['status'] = 'Rejected'
      flash(f"Download request rejected.", 'danger')
      break
  return redirect(url_for('admin_dashboard'))


@app.route('/toggle-auto-approval', methods=['POST'])
def toggle_auto_approval():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  ADMIN_SETTINGS['auto_approval_enabled'] = not ADMIN_SETTINGS.get('auto_approval_enabled', True)
  status_text = "Enabled" if ADMIN_SETTINGS['auto_approval_enabled'] else "Disabled"
  flash(f'Auto-approval has been {status_text} successfully!', 'success')
  return redirect(url_for('admin_dashboard'))


@app.route('/update-user-status/<int:user_id>/<status>', methods=['POST'])
def update_user_status(user_id, status):
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


@app.route('/approve-all-users', methods=['POST'])
def approve_all_users():
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


@app.route('/decline-all-users', methods=['POST'])
def decline_all_users():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  ADMIN_ACTIVITY['last_active'] = datetime.now()
  for user in REGISTERED_USERS:
    if user['status'] == 'Pending':
      user['status'] = 'Pending'
  flash('All pending users declined successfully!', 'success')
  return redirect(url_for('admin_dashboard'))


@app.route('/upload-master-category', methods=['GET', 'POST'])
def upload_master_category():
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
            flash(f'{category.capitalize()} funds updated permanently in database!', 'success')
    except Exception as e:
      flash(f'Error updating category: {e}', 'danger')
  return redirect(url_for('admin_dashboard'))


@app.route('/upload-nav', methods=['GET', 'POST'])
def upload_nav():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  ADMIN_ACTIVITY['last_active'] = datetime.now()
  if request.method == 'POST':
    try:
      file = request.files.get('nav_image')
      if file and file.filename != '':
        raw_fn = file.filename
        filename = secure_filename(raw_fn) or f'{datetime.now().strftime("%d-%m-%Y")}.jpg'
        file_path_upload = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        latest_ref_path = os.path.join(app.config['UPLOAD_FOLDER'], 'latest_nav.jpg')

        try:
          img = Image.open(file)
          img.thumbnail((1600, 1600))
          img.save(file_path_upload, optimize=True, quality=85)
          img.save(latest_ref_path, optimize=True, quality=85)
        except Exception:
          file.seek(0)
          file_bytes = file.read()
          with open(file_path_upload, 'wb') as f:
            f.write(file_bytes)
          with open(latest_ref_path, 'wb') as f:
            f.write(file_bytes)

        meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
        with open(meta_path, 'w') as mf:
          json.dump({'filename': filename, 'original_filename': raw_fn, 'upload_time': datetime.now().isoformat()}, mf)

        target_year, target_month = extract_date_from_filename(raw_fn)
        archive_target_dir = os.path.join(ARCHIVE_FOLDER, target_year, target_month)
        os.makedirs(archive_target_dir, exist_ok=True)
        shutil.copy(file_path_upload, os.path.join(archive_target_dir, filename))

        flash(f'Successfully published NAV: {filename}', 'success')
    except Exception as e:
      flash(f'Error uploading NAV image: {e}', 'danger')
  return redirect(url_for('admin_dashboard'))


@app.route('/upload-archive', methods=['GET', 'POST'])
def upload_archive():
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


@app.route('/get-archive-files', methods=['GET'])
def get_archive_files():
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
  app.run(debug=True)