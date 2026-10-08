from datetime import datetime, timedelta, timezone
import json
import os
import random
import shutil
import threading
import time
import urllib.request
import pandas as pd
import yfinance as yf
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

app = Flask(__name__)
app.secret_key = 'nav_updates_secret_key'

app.permanent_session_lifetime = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# Initialize Supabase Database Connection via Render Environment Variable[cite: 15]
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL) if DATABASE_URL else None

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ARCHIVE_FOLDER = 'archive_nav'
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

# Track last admin activity timestamp for online/offline status[cite: 15]
ADMIN_ACTIVITY = {'last_active': datetime.now()}

ADMIN_EMAIL = "bijooshpadmakumar522@gmail.com"

REGISTERED_USERS = [
    {
        'id': 1,
        'name': 'Rahul Sharma',
        'mobile': '+91 9876543210',
        'status': 'Pending',
        'registered_at': datetime.now() - timedelta(minutes=15),
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
  now = datetime.now()
  if user['status'] == 'Pending':
    reg_time = user.get('registered_at', now)
    if now - reg_time > timedelta(minutes=18):
      user['status'] = 'Approved'
      user['approved_at'] = now.isoformat()

  if user['status'] == 'Approved' and user.get('approved_at'):
    approved_date = datetime.fromisoformat(user['approved_at'])
    if now - approved_date > timedelta(days=30):
      user['status'] = 'Pending'
      user['approved_at'] = None
      user['registered_at'] = now


def send_email_notification(subject, body):
  sender_email = os.getenv("MAIL_USERNAME", "bijooshpadmakumar522@gmail.com")
  sender_password = os.getenv("MAIL_PASSWORD", "")
  if not sender_password:
    print("Email password not configured in environment variables (MAIL_PASSWORD).")
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
    print(f"Email sent successfully: {subject}")
  except Exception as e:
    print(f"Failed to send email: {e}")


def daily_scheduler():
  last_8am_sent = None
  last_10pm_sent = None
  while True:
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    current_date = ist_now.date()
    current_hour = ist_now.hour
    current_minute = ist_now.minute

    if current_hour == 8 and current_minute == 0 and last_8am_sent != current_date:
      body = "Good Morning Bijoosh,\n\nThis is your daily reminder to upload today's latest NAV data on the Admin Portal.\n\nBest Regards,\nNAV Portal Automated System"
      send_email_notification("Reminder: Upload Today's Latest NAV Data (8:00 AM)", body)
      last_8am_sent = current_date

    if current_hour == 22 and current_minute == 0 and last_10pm_sent != current_date:
      user_summary = "Here is the daily summary of registered users and their details:\n\n"
      for u in REGISTERED_USERS:
        user_summary += f"- Name: {u['name']} | Mobile: {u['mobile']} | Status: {u['status']}\n"
      user_summary += "\nBest Regards,\nNAV Portal Automated System"
      send_email_notification("Daily User Details Report (10:00 PM)", user_summary)
      last_10pm_sent = current_date

    time.sleep(30)


threading.Thread(target=daily_scheduler, daemon=True).start()


# Shared File-Based Cache for Gunicorn Multi-Worker Synchronization on Render
CACHE_FILE = 'sensex_cache.json'

DEFAULT_SENSEX_CACHE = {
    'value': 71459.37,
    'base_change_pts': -1179.34,
    'pct_change': -1.62,
    'is_positive': False,
    'last_close_time': '03:32:27 PM GMT+5:30',
    'trend_data': [
        {'date': '01 Oct', 'value': '71,909.70', 'change': -570.59},
        {'date': '05 Oct', 'value': '72,382.47', 'change': 472.77},
        {'date': '06 Oct', 'value': '73,067.81', 'change': 685.34},
        {'date': '07 Oct', 'value': '72,638.70', 'change': -429.11},
        {'date': '08 Oct', 'value': '71,459.37', 'change': -1179.34},
    ]
}


def load_sensex_cache():
  try:
    if os.path.exists(CACHE_FILE):
      with open(CACHE_FILE, 'r') as f:
        return json.load(f)
  except Exception as e:
    print(f"Error loading cache file: {e}")
  return DEFAULT_SENSEX_CACHE.copy()


def save_sensex_cache(cache_data):
  try:
    with open(CACHE_FILE, 'w') as f:
      json.dump(cache_data, f)
  except Exception as e:
    print(f"Error saving cache file: {e}")


if not os.path.exists(CACHE_FILE):
  save_sensex_cache(DEFAULT_SENSEX_CACHE)


def sync_sensex_from_yahoo():
  while True:
    try:
      cache = load_sensex_cache()
      url = "https://query1.finance.yahoo.com/v8/finance/chart/^BSESN?interval=1m&range=1d"
      req = urllib.request.Request(
          url,
          headers={
              "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
          }
      )
      with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode())
        meta = data['chart']['result'][0]['meta']
        current_val = float(meta['regularMarketPrice'])
        prev_close = float(meta.get('chartPreviousClose', meta.get('previousClose', current_val)))
        
        pts_change = round(current_val - prev_close, 2)
        pct_change = round((pts_change / prev_close) * 100, 2) if prev_close else 0.0

        cache['value'] = round(current_val, 2)
        cache['base_change_pts'] = pts_change
        cache['pct_change'] = pct_change
        cache['is_positive'] = pts_change >= 0

        now_utc = datetime.now(timezone.utc)
        ist_now = now_utc + timedelta(hours=5, minutes=30)
        today_date_str = ist_now.strftime('%d %b')
        
        found_today = False
        for item in cache['trend_data']:
          if item['date'] == today_date_str:
            item['value'] = f"{cache['value']:,.2f}"
            item['change'] = cache['base_change_pts']
            found_today = True
            break
        if not found_today:
          cache['trend_data'].append({
              'date': today_date_str,
              'value': f"{cache['value']:,.2f}",
              'change': cache['base_change_pts']
          })
          if len(cache['trend_data']) > 5:
            cache['trend_data'].pop(0)

        save_sensex_cache(cache)
    except Exception as e:
      print(f'Sensex Yahoo API sync error: {e}')

    time.sleep(3)


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
    time_label = f"At close: {cache.get('last_close_time', '03:32:27 PM GMT+5:30')}"

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


def get_latest_nav_filename():
  try:
    standard_latest = 'latest_nav.jpg'
    if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], standard_latest)):
      return standard_latest

    files = os.listdir(app.config['UPLOAD_FOLDER'])
    image_files = [
        f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    if not image_files:
      return None
    valid_date_files = []
    for f in image_files:
      base_name = os.path.splitext(f)[0]
      try:
        file_date = datetime.strptime(base_name, '%d-%m-%Y')
        valid_date_files.append((file_date, f))
      except ValueError:
        pass
    if valid_date_files:
      valid_date_files.sort(key=lambda x: x[0], reverse=True)
      return valid_date_files[0][1]
    return max(
        image_files,
        key=lambda x: os.path.getmtime(
            os.path.join(app.config['UPLOAD_FOLDER'], x)
        ),
    )
  except Exception as e:
    print(f'Error resolving latest NAV: {e}')
    return None


@app.route('/')
def home():
  return redirect(url_for('login'))


@app.route('/health')
def health_check():
  return 'OK', 200


@app.route('/login', methods=['GET', 'POST'])
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
  
  utc_now = datetime.now(timezone.utc)
  ist_now = utc_now + timedelta(hours=5, minutes=30)
  today_ist = ist_now.strftime('%d-%m-%Y')
  today_alt = ist_now.strftime('%Y-%m-%d')

  latest_data_updated = False
  try:
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    for f in files:
      if f != 'latest_nav.jpg' and (today_ist in f or today_alt in f):
        latest_data_updated = True
        break
  except Exception as e:
    print(f"Error checking today's upload: {e}")

  admin_online = (datetime.now() - ADMIN_ACTIVITY['last_active']) < timedelta(minutes=5)

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
  return render_template(
      'admin_dashboard.html',
      sensex=sensex_info,
      sensex_trend=sensex_trend_data,
      users=REGISTERED_USERS,
      feedbacks=USER_FEEDBACKS,
      equity_data=parse_fund_excel_from_db('equity_funds'),
      balancer_data=parse_fund_excel_from_db('balancer_funds'),
      debt_data=parse_fund_excel_from_db('debt_funds'),
      current_time=datetime.now().strftime('%b %d, %Y, %I:%M:%S %p'),
  )


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
            flash(
                f'{category.capitalize()} funds updated permanently in Supabase!',
                'success',
            )
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
      saved_any = False
      for key in request.files:
        for file in request.files.getlist(key):
          if file and file.filename != '':
            filename = secure_filename(file.filename)
            if not filename:
              filename = f'nav_{int(datetime.now().timestamp())}.jpg'

            file_path_upload = os.path.join(
                app.config['UPLOAD_FOLDER'], filename
            )
            file.save(file_path_upload)

            # ALWAYS create/update a standardized 'latest_nav.jpg' reference copy[cite: 15]
            latest_ref_path = os.path.join(app.config['UPLOAD_FOLDER'], 'latest_nav.jpg')
            shutil.copy(file_path_upload, latest_ref_path)

            base_name = os.path.splitext(filename)[0]
            file_date = None
            for fmt in (
                '%d-%m-%Y',
                '%Y-%m-%d',
                '%d_%m_%Y',
                '%Y_%m_%d',
                '%d%m%Y',
            ):
              try:
                file_date = datetime.strptime(base_name[:10], fmt)
                break
              except ValueError:
                pass

            if not file_date:
              file_date = datetime.now()

            year_str = str(file_date.year)
            month_name = file_date.strftime('%B')
            month_num = file_date.strftime('%m')

            archive_month_dir = os.path.join(
                ARCHIVE_FOLDER, year_str, f'{month_num}_{month_name}'
            )
            os.makedirs(archive_month_dir, exist_ok=True)

            file_path_archive = os.path.join(archive_month_dir, filename)
            shutil.copy(file_path_upload, file_path_archive)

            saved_any = True

      if saved_any:
        flash(
            'NAV Image uploaded and automatically archived successfully!',
            'success',
        )
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
      saved_any = False
      for key in request.files:
        for file in request.files.getlist(key):
          if file and file.filename != '':
            filename = secure_filename(file.filename)
            if not filename:
              filename = (
                  f'archive_{int(datetime.now().timestamp())}_{file.filename}'
              )
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            saved_any = True
      if saved_any:
        flash('Archive files uploaded successfully!', 'success')
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
      'jan': '01',
      'feb': '02',
      'mar': '03',
      'apr': '04',
      'may': '05',
      'jun': '06',
      'jul': '07',
      'aug': '08',
      'sep': '09',
      'oct': '10',
      'nov': '11',
      'dec': '12',
  }

  target_month_num = None
  for k, v in month_map.items():
    if k in month_input:
      target_month_num = v
      break

  try:
    year_dir = os.path.join(ARCHIVE_FOLDER, year)
    if os.path.exists(year_dir):
      for d in os.listdir(year_dir):
        if (
            month_input in d.lower()
            or (target_month_num and target_month_num in d)
        ):
          target_month_dir = os.path.join(year_dir, d)
          if os.path.exists(target_month_dir):
            for root, dirs, files in os.walk(target_month_dir):
              for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                  matched_files.add(f)

    upload_files = os.listdir(app.config['UPLOAD_FOLDER'])
    for f in upload_files:
      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')) and f != 'latest_nav.jpg':
        is_matched = False
        base_name = os.path.splitext(f)[0]

        parsed_date = None
        for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%d_%m_%Y', '%Y_%m_%d'):
          try:
            parsed_date = datetime.strptime(base_name[:10], fmt)
            break
          except ValueError:
            pass

        if parsed_date:
          file_year = str(parsed_date.year)
          file_month_num = f'{parsed_date.month:02d}'
          if file_year == year and file_month_num == target_month_num:
            is_matched = True
        else:
          if year in f and (
              (target_month_num and f'-{target_month_num}-' in f)
              or (month_input and month_input in f.lower())
          ):
            is_matched = True

        if is_matched:
          matched_files.add(f)

    sorted_files = sorted(list(matched_files), reverse=True)
    return jsonify({'success': True, 'files': sorted_files})
  except Exception as e:
    print(f'Error in get_archive_files: {e}')
    return jsonify({'success': False, 'files': []})


@app.route('/view-archive-file/<filename>')
def view_archive_file(filename):
  as_attachment = request.args.get('download') == 'true'
  for root, dirs, files in os.walk(ARCHIVE_FOLDER):
    if filename in files:
      return send_from_directory(root, filename, as_attachment=as_attachment)
  return send_from_directory(
      app.config['UPLOAD_FOLDER'], filename, as_attachment=as_attachment
  )


@app.route('/download-latest-nav')
def download_latest_nav():
  try:
    latest_file = get_latest_nav_filename()
    if latest_file:
      return send_from_directory(
          app.config['UPLOAD_FOLDER'], latest_file, as_attachment=True
      )
  except Exception as e:
    print(f'Download error: {e}')
  flash('No NAV image available for download.', 'danger')
  return redirect(url_for('user_dashboard'))


if __name__ == '__main__':
  app.run(debug=True)