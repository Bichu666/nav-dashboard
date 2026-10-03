from datetime import datetime, timedelta
import json
import os
import shutil
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
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'nav_updates_secret_key'

app.permanent_session_lifetime = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# Initialize Supabase Database Connection via Render Environment Variable
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL) if DATABASE_URL else None

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ARCHIVE_FOLDER = 'archive_nav'
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

REGISTERED_USERS = [
    {
        'id': 1,
        'name': 'Rahul Sharma',
        'mobile': '+91 9876543210',
        'status': 'Pending',
        'approved_at': None,
    },
    {
        'id': 2,
        'name': 'Priya Nair',
        'mobile': '+91 9876522888',
        'status': 'Approved',
        'approved_at': datetime.now().isoformat(),
    },
    {
        'id': 3,
        'name': 'biju',
        'mobile': '+917034788666',
        'status': 'Approved',
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
  if user['status'] == 'Approved' and user.get('approved_at'):
    approved_date = datetime.fromisoformat(user['approved_at'])
    if datetime.now() - approved_date > timedelta(days=30):
      user['status'] = 'Pending'
      user['approved_at'] = None


def get_sensex_data():
  try:
    sensex = yf.Ticker('^BSESN')
    df = sensex.history(period='10d')
    if not df.empty:
      latest_row = df.iloc[-1]
      current_val = round(latest_row['Close'], 2)
      prev_val = df.iloc[-2]['Close'] if len(df) > 1 else latest_row['Open']
      pts_change = round(current_val - prev_val, 2)
      pct_change = round((pts_change / prev_val) * 100, 2) if prev_val else 0.0

      recent_5 = df.tail(5)
      trend_data = []
      p_close = None

      for index, row in recent_5.iterrows():
        date_str = index.strftime('%d %b')
        close_val = round(row['Close'], 2)
        chg = round(close_val - p_close, 2) if p_close is not None else 0.0
        trend_data.append({
            'date': date_str,
            'value': f'{close_val:,.2f}',
            'change': chg,
        })
        p_close = close_val

      live_info = {
          'value': f'{current_val:,.2f}',
          'change': f'{pts_change:+,.2f} pts ({pct_change:+.2f}%)',
          'is_positive': pts_change >= 0,
      }
      return live_info, trend_data
  except Exception as e:
    print(f'yfinance fetch error: {e}')

  try:
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/^BSESN?range=10d&interval=1d'
    req = urllib.request.Request(
        url, headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, timeout=5) as response:
      data = json.loads(response.read().decode())
      result = data['chart']['result'][0]
      timestamps = result['timestamp']
      closes = result['indicators']['quote'][0]['close']

      valid_data = []
      for ts, cl in zip(timestamps, closes):
        if cl is not None:
          dt = datetime.fromtimestamp(ts)
          valid_data.append(
              {'date': dt.strftime('%d %b'), 'close': round(cl, 2)}
          )

      if valid_data:
        current_val = valid_data[-1]['close']
        prev_val = (
            valid_data[-2]['close']
            if len(valid_data) > 1
            else valid_data[-1]['close']
        )
        pts_change = round(current_val - prev_val, 2)
        pct_change = (
            round((pts_change / prev_val) * 100, 2) if prev_val else 0.0
        )

        recent_5 = valid_data[-5:]
        trend_data = []
        p_close = None
        for item in recent_5:
          chg = (
              round(item['close'] - p_close, 2) if p_close is not None else 0.0
          )
          trend_data.append({
              'date': item['date'],
              'value': f'{item["close"]:,.2f}',
              'change': chg,
          })
          p_close = item['close']

        live_info = {
            'value': f'{current_val:,.2f}',
            'change': f'{pts_change:+,.2f} pts ({pct_change:+.2f}%)',
            'is_positive': pts_change >= 0,
        }
        return live_info, trend_data
  except Exception as alt_e:
    print(f'Alternative Sensex fetch error: {alt_e}')

  live_info = {
      'value': '81,235.40',
      'change': '+312.50 pts (+0.39%)',
      'is_positive': True,
  }
  trend_data = [
      {'date': '24 Sep', 'value': '80,500.10', 'change': 120.00},
      {'date': '25 Sep', 'value': '80,850.20', 'change': 350.10},
      {'date': '26 Sep', 'value': '80,620.00', 'change': -230.20},
      {'date': '29 Sep', 'value': '80,922.90', 'change': 302.90},
      {'date': '30 Sep', 'value': '81,235.40', 'change': 312.50},
  ]
  return live_info, trend_data


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
  if user_record and user_record['status'] == 'Approved':
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
  
  # Check if a file for today's date exists in the upload folder
  today_str = datetime.now().strftime('%d-%m-%Y')
  latest_data_updated = False
  try:
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    if any(today_str in f for f in files):
      latest_data_updated = True
  except Exception as e:
    print(f"Error checking today's upload: {e}")

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
  for user in REGISTERED_USERS:
    if user['id'] == user_id:
      user['status'] = status.capitalize()
      if status.capitalize() == 'Approved':
        user['approved_at'] = datetime.now().isoformat()
      else:
        user['approved_at'] = None
  return redirect(url_for('admin_dashboard'))


@app.route('/upload-master-category', methods=['GET', 'POST'])
def upload_master_category():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
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
  if request.method == 'POST':
    try:
      saved_any = False
      for key in request.files:
        for file in request.files.getlist(key):
          if file and file.filename != '':
            filename = secure_filename(file.filename)
            if not filename:
              filename = f'nav_{int(datetime.now().timestamp())}.jpg'

            # 1. Save to main UPLOAD_FOLDER for latest NAV tracking
            file_path_upload = os.path.join(
                app.config['UPLOAD_FOLDER'], filename
            )
            file.save(file_path_upload)

            # 2. Automatically extract date from filename or fallback to current datetime
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
            month_name = file_date.strftime('%B')  # e.g., 'October'
            month_num = file_date.strftime('%m')  # e.g., '10'

            # 3. Automatically route and save into archive year/month folder
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
      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
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