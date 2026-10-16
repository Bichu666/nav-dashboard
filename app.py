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
  m, d, y = ist_now.month, ist_now.day, ist_now.year

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

DEFAULT_SENSEX_CACHE = {
    'value': 74595.96,
    'base_change_pts': 280.35,
    'pct_change': 0.38,
    'is_positive': True,
    'last_close_time': '10:52:10 AM GMT+5:30',
    'trend_data': [
        {'date': '12 Oct', 'value': '71,924.68', 'change': -547.65},
        {'date': '13 Oct', 'value': '73,033.78', 'change': 1109.10},
        {'date': '14 Oct', 'value': '72,781.89', 'change': -251.89},
        {'date': '15 Oct', 'value': '74,315.61', 'change': 1533.72},
        {'date': '16 Oct', 'value': '74,595.96', 'change': 280.35},
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

        cache = load_sensex_cache()
        cache['value'] = round(current_val, 2)
        cache['base_change_pts'] = round(pts_change, 2)
        cache['pct_change'] = round(pct_change, 2)
        cache['is_positive'] = pts_change >= 0
        if trend_list:
          cache['trend_data'] = trend_list[-5:]

        save_sensex_cache(cache)
    except Exception as e:
      print(f"Sensex sync background error: {e}")

    time.sleep(15)


threading.Thread(target=sync_sensex_from_yahoo, daemon=True).start()


def get_sensex_data():
  cache = load_sensex_cache()
  now_utc = datetime.now(timezone.utc)
  ist_now = now_utc + timedelta(hours=5, minutes=30)
  weekday = ist_now.weekday()
  current_total_minutes = ist_now.hour * 60 + ist_now.minute

  is_market_open = (0 <= weekday <= 4) and (555 <= current_total_minutes <= 930)

  current_val = cache['value']
  pts_change = cache['base_change_pts']
  pct_change = cache['pct_change']

  if is_market_open:
    time_label = f"Live as of: {ist_now.strftime('%b %d, %Y, %I:%M:%S %p')}"
  else:
    time_label = f"At close: {cache.get('last_close_time', '03:28:40 PM GMT+5:30')}"

  live_info = {
      'value': f'{current_val:,.2f}',
      'change': f'{pts_change:+,.2f} pts ({pct_change:+.2f}%)',
      'is_positive': pts_change >= 0,
      'time_label': time_label,
      'is_market_open': is_market_open,
  }
  return live_info, cache['trend_data']


@app.route('/api/sensex-live')
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
      'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'
  }
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
@limiter.limit("5 per minute")
def login():
  if request.method == 'POST':
    username = request.form.get('username')
    mobile = request.form.get('mobile')
    if username and mobile:
      session.permanent = True
      session['username'] = username
      session['mobile'] = mobile
      user_record = next(
          (u for u in REGISTERED_USERS if u['mobile'] == mobile), None
      )
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
  return render_template('login.html')


@app.route('/pending-approval')
def pending_approval():
  return render_template('pending_approval.html', username=session.get('username', 'User'))


@app.route('/user-dashboard')
def user_dashboard():
  mobile = session.get('mobile', '')
  sensex_info, sensex_trend_data = get_sensex_data()
  admin_online = (datetime.now() - ADMIN_ACTIVITY['last_active']) < timedelta(minutes=5)
  festival_greeting = get_festival_greeting()

  latest_data_updated = False
  try:
    meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
    if os.path.exists(meta_path):
      with open(meta_path, 'r') as mf:
        meta = json.load(mf)
        if is_today_filename(meta.get('filename', ''), meta.get('upload_time', '')):
          latest_data_updated = True
  except Exception:
    pass

  return render_template(
      'user_dashboard.html',
      username=session.get('username', 'Client'),
      mobile=mobile,
      sensex=sensex_info,
      sensex_trend=sensex_trend_data,
      equity_data=parse_fund_excel_from_db('equity_funds'),
      balancer_data=parse_fund_excel_from_db('balancer_funds'),
      debt_data=parse_fund_excel_from_db('debt_funds'),
      latest_data_updated=latest_data_updated,
      admin_online=admin_online,
      festival_greeting=festival_greeting,
  )


@app.route('/admin-login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
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


@app.route('/admin-dashboard', methods=['GET', 'POST'])
def admin_dashboard():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))

  ADMIN_ACTIVITY['last_active'] = datetime.now()

  for user in REGISTERED_USERS:
    check_user_validity(user)

  sensex_info, sensex_trend_data = get_sensex_data()
  return render_template(
      'admin_dashboard.html',
      sensex=sensex_info,
      sensex_trend=sensex_trend_data,
      users=REGISTERED_USERS,
      feedbacks=USER_FEEDBACKS,
      equity_data=parse_fund_excel_from_db('equity_funds'),
      balancer_data=parse_fund_excel_from_db('balancer_funds'),
      debt_data=parse_fund_excel_from_db('debt_funds'),
      auto_approval_enabled=ADMIN_SETTINGS['auto_approval_enabled'],
      current_time=datetime.now().strftime('%b %d, %Y, %I:%M:%S %p'),
  )


@app.route('/upload-master-category', methods=['POST'])
def upload_master_category():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  try:
    category = request.form.get('category')
    file_key = f'{category}_file'
    if file_key in request.files:
      file = request.files[file_key]
      if file and file.filename != '':
        df = pd.read_excel(file)
        if engine:
          df.to_sql(f'{category}_funds', engine, if_exists='replace', index=False)
          flash(f'{category.capitalize()} funds updated successfully!', 'success')
  except Exception as e:
    flash(f'Error: {e}', 'danger')
  return redirect(url_for('admin_dashboard'))


@app.route('/upload-nav', methods=['POST'])
def upload_nav():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  try:
    file = request.files.get('nav_image')
    if file and file.filename != '':
      filename = secure_filename(file.filename)
      file_bytes = file.read()

      with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'wb') as f:
        f.write(file_bytes)
      with open(os.path.join(app.config['UPLOAD_FOLDER'], 'latest_nav.jpg'), 'wb') as f:
        f.write(file_bytes)

      meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
      with open(meta_path, 'w') as mf:
        json.dump({'filename': filename, 'upload_time': datetime.now().isoformat()}, mf)

      flash('NAV published successfully!', 'success')
  except Exception as e:
    flash(f'Error: {e}', 'danger')
  return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
  app.run(debug=True)