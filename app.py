from datetime import datetime, timedelta, timezone
import json
import os
import random
import re
import shutil
import threading
import time
import pandas as pd
import yfinance as yf
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

      (2027, 1, 1): "Happy New Year",
      (2027, 1, 26): "Happy Republic Day",
      (2027, 3, 22): "Happy Holi",
      (2027, 8, 15): "Happy Independence Day",
      (2027, 9, 12): "Happy Onam",
      (2027, 10, 29): "Happy Diwali",
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
    'value': 72779.17,
    'base_change_pts': -254.61,
    'pct_change': -0.35,
    'is_positive': False,
    'last_close_time': '03:28:40 PM GMT+5:30',
    'trend_data': [
        {'date': '07 Oct', 'value': '72,638.70', 'change': -429.11},
        {'date': '09 Oct', 'value': '72,472.33', 'change': 879.09},
        {'date': '12 Oct', 'value': '72,976.53', 'change': 1051.85},
        {'date': '13 Oct', 'value': '73,033.78', 'change': 561.48},
        {'date': '14 Oct', 'value': '72,779.17', 'change': -254.61},
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


def sync_sensex_from_yahoo():
  while True:
    try:
      current_val = 0
      prev_close = 0
      pts_change = 0
      pct_change = 0
      trend_list = []

      ticker = yf.Ticker("^BSESN")
      try:
        hist = ticker.history(period="5d", interval="1d")
        if hist is not None and not hist.empty:
          current_val = float(hist['Close'].iloc[-1])
          prev_close = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else current_val

          for idx, row in hist.iterrows():
            d_str = idx.strftime('%d %b')
            trend_list.append({
                'date': d_str,
                'value': f"{row['Close']:,.2f}",
                'change': round(float(row['Close'] - row['Open']), 2)
            })
      except Exception as ex:
        print(f"yfinance fetch warning: {ex}")

      if current_val > 0:
        if prev_close > 0:
          pts_change = round(current_val - prev_close, 2)
          pct_change = round((pts_change / prev_close) * 100, 2)

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

    time.sleep(60)


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


@app.route('/user-dashboard')
def user_dashboard():
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

  sensex_info, sensex_trend_data = get_sensex_data()
  admin_online = (datetime.now() - ADMIN_ACTIVITY['last_active']) < timedelta(minutes=5)
  festival_greeting = get_festival_greeting()

  latest_data_updated = False
  try:
    meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
    if os.path.exists(meta_path):
      with open(meta_path, 'r') as mf:
        meta = json.load(mf)
        last_fn = meta.get('filename', '')
        last_time = meta.get('upload_time', '')
        if is_today_filename(last_fn, last_time):
          latest_data_updated = True
  except Exception as e:
    print(f"Error checking upload status: {e}")

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


@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
  if 'username' not in session:
    return redirect(url_for('login'))
  feedback_text = request.form.get('feedback')
  if feedback_text:
    USER_FEEDBACKS.append({
        'id': len(USER_FEEDBACKS) + 1,
        'username': session.get('username', 'Client'),
        'feedback': feedback_text,
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    })
    flash('Feedback submitted successfully!', 'success')
  return redirect(url_for('user_dashboard'))


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

  sensex_info, sensex_trend_data = get_sensex_data()
  festival_greeting = get_festival_greeting()

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
      festival_greeting=festival_greeting,
  )


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
      user['approved_at'] = None
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
            flash(f'{category.capitalize()} funds updated permanently in Supabase database!', 'success')
          else:
            flash('Database connection error.', 'danger')
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
        month_num_map = {'January':'01', 'February':'02', 'March':'03', 'April':'04', 'May':'05', 'June':'06', 'July':'07', 'August':'08', 'September':'09', 'October':'10', 'November':'11', 'December':'12'}
        m_num = month_num_map.get(target_month, '10')
        archive_target_dir = os.path.join(ARCHIVE_FOLDER, target_year, f'{m_num}_{target_month}')
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


@app.route('/upload-archive', methods=['GET', 'POST'])
def upload_archive():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  
  ADMIN_ACTIVITY['last_active'] = datetime.now()

  if request.method == 'POST':
    try:
      year = request.form.get('archive_year', datetime.now().strftime('%Y'))
      month_input = request.form.get('archive_month', 'Oct').strip().lower()

      month_map = {
          'jan': ('01', 'January'), 'feb': ('02', 'February'), 'mar': ('03', 'March'),
          'apr': ('04', 'April'), 'may': ('05', 'May'), 'jun': ('06', 'June'),
          'jul': ('07', 'July'), 'aug': ('08', 'August'), 'sep': ('09', 'September'),
          'oct': ('10', 'October'), 'nov': ('11', 'November'), 'dec': ('12', 'December')
      }
      m_num, full_month_name = month_map.get(month_input[:3], ('10', 'October'))

      saved_count = 0
      files = request.files.getlist('archive_files')
      for file in files:
        if file and file.filename != '':
          raw_fn = file.filename
          filename = secure_filename(raw_fn)
          if not filename:
            filename = f'{datetime.now().strftime("%d-%m-%Y")}.jpg'

          f_year, f_month = extract_date_from_filename(raw_fn)
          if f_year and f_month:
            f_num_map = {'January':'01', 'February':'02', 'March':'03', 'April':'04', 'May':'05', 'June':'06', 'July':'07', 'August':'08', 'September':'09', 'October':'10', 'November':'11', 'December':'12'}
            target_dir = os.path.join(ARCHIVE_FOLDER, f_year, f'{f_num_map.get(f_month, m_num)}_{f_month}')
          else:
            target_dir = os.path.join(ARCHIVE_FOLDER, year, f'{m_num}_{full_month_name}')

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


@app.route('/get-archive-files', methods=['GET'])
def get_archive_files():
  year = request.args.get('year', '').strip()
  month_input = request.args.get('month', '').strip().lower()
  matched_files = set()

  month_map = {
      'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
      'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
      'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
  }
  target_m_num = month_map.get(month_input[:3], '10')

  try:
    search_dirs = [ARCHIVE_FOLDER, UPLOAD_FOLDER]
    for s_dir in search_dirs:
      if os.path.exists(s_dir):
        for root, dirs, files in os.walk(s_dir):
          for f in files:
            if not f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')) or f == 'latest_nav.jpg':
              continue
            
            clean_name = os.path.splitext(f)[0]
            parts = re.split(r'[-_.]', clean_name)
            
            if len(parts) >= 3 and len(parts[0]) <= 2 and len(parts[1]) <= 2 and len(parts[2]) == 4:
              f_day, f_month, f_year = parts[0].zfill(2), parts[1].zfill(2), parts[2]
              
              if year and f_year != year:
                continue
              if month_input and f_month != target_m_num:
                continue
              
              matched_files.add(f)
            else:
              if year and (year in f or year in root):
                if month_input and (f'/{target_m_num}_' in root.lower() or f'_{target_m_num}_' in f.lower()):
                  matched_files.add(f)

    sorted_files = sorted(list(matched_files), reverse=True)
    return jsonify({'success': True, 'files': sorted_files})
  except Exception as e:
    print(f'Error in get_archive_files: {e}')
    return jsonify({'success': False, 'files': []})


@app.route('/view-archive-file/<path:filename>')
def view_archive_file(filename):
  archive_base = ARCHIVE_FOLDER
  for root, dirs, files in os.walk(archive_base):
    if filename in files:
      return send_from_directory(root, filename)
  return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/download-latest-nav')
def download_latest_nav():
  latest_path = os.path.join(app.config['UPLOAD_FOLDER'], 'latest_nav.jpg')
  if os.path.exists(latest_path):
    return send_from_directory(app.config['UPLOAD_FOLDER'], 'latest_nav.jpg', as_attachment=True)
  
  try:
    files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if files:
      files.sort(key=lambda x: os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], x)), reverse=True)
      return send_from_directory(app.config['UPLOAD_FOLDER'], files[0], as_attachment=True)
  except Exception:
    pass
  return "No NAV image found. Please upload today's NAV from the Admin Portal.", 404


if __name__ == '__main__':
  app.run(debug=True)