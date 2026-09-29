import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_from_directory,
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'nav_updates_secret_key'

app.permanent_session_lifetime = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
    if df.empty:
      raise ValueError('Empty dataframe')

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
    print(f'Error fetching Sensex data: {e}')
    live_info = {
        'value': '74,895.74',
        'change': '+315.20 pts (+0.42%)',
        'is_positive': True,
    }
    trend_data = [
        {'date': '21 Sep', 'value': '74,858.99', 'change': 0.0},
        {'date': '22 Sep', 'value': '74,528.08', 'change': -330.91},
        {'date': '23 Sep', 'value': '74,828.25', 'change': 300.17},
        {'date': '24 Sep', 'value': '73,580.54', 'change': -1247.71},
        {'date': '25 Sep', 'value': '74,895.74', 'change': 1315.20},
    ]
    return live_info, trend_data


def format_pct(val):
  try:
    return round(float(val) * 100, 2)
  except:
    return val


def parse_fund_excel(filename):
  fund_list = []
  path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
  if os.path.exists(path):
    try:
      df = pd.read_excel(path)
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
      print(f'Error reading {filename}: {e}')
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
  return render_template(
      'user_dashboard.html',
      username=session.get('username', 'Client'),
      mobile=mobile,
      sensex=sensex_info,
      sensex_trend=sensex_trend_data,
      equity_data=parse_fund_excel('equity_funds.xlsx'),
      balancer_data=parse_fund_excel('balancer_funds.xlsx'),
      debt_data=parse_fund_excel('debt_funds.xlsx'),
  )


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
      equity_data=parse_fund_excel('equity_funds.xlsx'),
      balancer_data=parse_fund_excel('balancer_funds.xlsx'),
      debt_data=parse_fund_excel('debt_funds.xlsx'),
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
          filename = f'{category}_funds.xlsx'
          file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
          flash(f'{category.capitalize()} funds updated successfully!', 'success')
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
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            saved_any = True
      if saved_any:
        flash('NAV Image uploaded successfully!', 'success')
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
  year = request.args.get('year', '')
  month = request.args.get('month', '')
  month_map = {
      'Jan': '01',
      'Feb': '02',
      'Mar': '03',
      'Apr': '04',
      'May': '05',
      'Jun': '06',
      'Jul': '07',
      'Aug': '08',
      'Sep': '09',
      'Oct': '10',
      'Nov': '11',
      'Dec': '12',
  }
  try:
    all_files = os.listdir(app.config['UPLOAD_FOLDER'])
    numeric_month = month_map.get(month, '')
    matched_files = []
    for f in all_files:
      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')) and year in f:
        if numeric_month:
          if (
              f'-{numeric_month}-' in f
              or f'/{numeric_month}/' in f
              or f'_{numeric_month}_' in f
              or f'-{numeric_month}.' in f
              or f'_{numeric_month}.' in f
          ):
            matched_files.append(f)
        else:
          if month.lower() in f.lower():
            matched_files.append(f)
    matched_files.sort(reverse=True)
    return jsonify({'success': True, 'files': matched_files})
  except Exception as e:
    return jsonify({'success': False, 'files': []})


@app.route('/view-archive-file/<filename>')
def view_archive_file(filename):
  as_attachment = request.args.get('download') == 'true'
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