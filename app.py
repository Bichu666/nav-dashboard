from datetime import datetime, timedelta, timezone
import json
import os
import re
import shutil
import smtplib
import threading
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
import pandas as pd
import requests
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'nav_updates_secret_key'
app.permanent_session_lifetime = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["10000 per day", "1000 per hour"],
    storage_uri="memory://",
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
]

USER_FEEDBACKS = [
    {
        'id': 1,
        'username': 'Rahul Sharma',
        'feedback': 'Great portal! Very intuitive and fast NAV updates.',
        'rating': 5,
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    }
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
  m, d, y = ist_now.month, ist_now.day, ist_now.year

  festivals_by_date = {
      (2026, 1, 1): "Happy New Year",
      (2026, 1, 26): "Happy Republic Day",
      (2026, 8, 15): "Happy Independence Day",
      (2026, 10, 20): "Happy Dussehra",
      (2026, 11, 8): "Happy Diwali",
      (2026, 12, 25): "Merry Christmas",
  }
  return festivals_by_date.get((y, m, d), None)


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


def extract_date_from_filename(filename):
  fn = filename.lower()
  clean_name = os.path.splitext(filename)[0]

  for fmt in (
      '%d-%m-%Y',
      '%d_%m_%Y',
      '%m-%d-%Y',
      '%m_%d_%Y',
      '%Y-%m-%d',
      '%Y_%m_%d',
      '%d.%m.%Y',
  ):
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
      'jan': 'January',
      'feb': 'February',
      'mar': 'March',
      'apr': 'April',
      'may': 'May',
      'jun': 'June',
      'jul': 'July',
      'aug': 'August',
      'sep': 'September',
      'oct': 'October',
      'nov': 'November',
      'dec': 'December',
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
@limiter.limit("10 per minute")
def login():
  if request.method == 'POST':
    username = request.form.get('username', '').strip()
    mobile = request.form.get('mobile', '').strip()

    name_is_valid = bool(re.match(r'^[A-Za-z\s]+$', username))
    clean_mobile = re.sub(r'\D', '', mobile)
    mobile_is_valid = 10 <= len(clean_mobile) <= 12

    if not name_is_valid:
      flash(
          'Please use a correct name containing only letters (no numbers or'
          ' symbols).',
          'danger',
      )
      return render_template('login.html')

    if not mobile_is_valid:
      flash('Please enter a valid 10-digit mobile number.', 'danger')
      return render_template('login.html')

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

  admin_online = (datetime.now() - ADMIN_ACTIVITY['last_active']) < timedelta(
      minutes=5
  )
  festival_greeting = get_festival_greeting()

  sensex_info = {
      'value': '74,729.27',
      'change': '+413.66 pts (+0.56%)',
      'is_positive': True,
      'time_label': 'Live Market Feed',
  }
  sensex_trend_data = [
      {'date': '12 Oct', 'value': '71,924.68', 'change': -846.64},
      {'date': '13 Oct', 'value': '73,033.78', 'change': 1082.05},
      {'date': '14 Oct', 'value': '72,781.89', 'change': -267.87},
      {'date': '15 Oct', 'value': '74,315.61', 'change': 1533.72},
      {'date': '16 Oct', 'value': '74,729.27', 'change': 413.66},
  ]

  return render_template(
      'user_dashboard.html',
      username=session.get('username', 'Client'),
      mobile=mobile,
      sensex=sensex_info,
      sensex_trend=sensex_trend_data,
      equity_data=parse_fund_excel_from_db('equity_funds'),
      balancer_data=parse_fund_excel_from_db('balancer_funds'),
      debt_data=parse_fund_excel_from_db('debt_funds'),
      admin_online=admin_online,
      admin_mobile=ADMIN_MOBILE,
      festival_greeting=festival_greeting,
  )


@app.route('/request-download', methods=['POST'])
def request_download():
  if 'username' not in session:
    return jsonify({'success': False, 'message': 'Not logged in'})
  data = request.get_json() or {}
  
