import os
import traceback
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
    send_from_directory,
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'nav_updates_secret_key_comprehensive'
app.permanent_session_lifetime = timedelta(days=365)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_NAME = 'Bijoosh Padmakumar'

# Dummy state management for users and feedback
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
]

USER_FEEDBACK = [
    {
        'name': 'Priya Nair',
        'message': (
            'The monthly statement downloads are super helpful. Great UI!'
        ),
        'date': '27 Sep 2026',
    }
]


def format_pct(val):
  try:
    return round(float(val) * 100, 2)
  except:
    return val


def parse_fund_excel(filename):
  fund_list = []
  path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
  if not os.path.exists(path):
    path = filename  # Fallback to root directory if not found in uploads

  if os.path.exists(path):
    try:
      df = pd.read_excel(path)
      if not df.empty:
        df = df.dropna(subset=[df.columns[0]])
        for _, row in df.iterrows():
          val = str(row.iloc[0]).strip()
          if val and val.lower() not in ['nan', 'funds', 'unnamed: 0']:
            fund_list.append({
                'fund': val,
                'inception': (
                    str(row.iloc[1])
                    if len(row) > 1 and pd.notna(row.iloc[1])
                    else ''
                ),
                'benchmark': (
                    str(row.iloc[2])
                    if len(row) > 2 and pd.notna(row.iloc[2])
                    else ''
                ),
                'since': (
                    format_pct(row.iloc[3])
                    if len(row) > 3 and pd.notna(row.iloc[3])
                    else '0'
                ),
                'high': (
                    str(row.iloc[13])
                    if len(row) > 13 and pd.notna(row.iloc[13])
                    else '0'
                ),
                'latest': (
                    str(row.iloc[14])
                    if len(row) > 14 and pd.notna(row.iloc[14])
                    else '0'
                ),
            })
    except Exception as e:
      print(f'Error reading {filename}: {e}')
  return fund_list


def get_recent_sensex():
  try:
    sensex = yf.Ticker('^BSESN')
    df = sensex.history(period='10d')
    if df.empty or len(df) < 5:
      raise ValueError('Insufficient rows')
    recent_5 = df.tail(5)
    trend_data = []
    prev_close = None
    for index, row in recent_5.iterrows():
      date_str = index.strftime('%d %b')
      close_val = round(row['Close'], 2)
      # Displaying point changes instead of percentages if preferred, or both
      change_pts = (
          round(close_val - prev_close, 2) if prev_close else 0.0
      )
      trend_data.append(
          {'date': date_str, 'value': close_val, 'change': change_pts}
      )
      prev_close = close_val
    return trend_data
  except:
    return [
        {'date': '21 Sep', 'value': 74858.99, 'change': +120.50},
        {'date': '22 Sep', 'value': 74529.08, 'change': -329.91},
        {'date': '23 Sep', 'value': 74828.25, 'change': +299.17},
        {'date': '24 Sep', 'value': 73580.54, 'change': -1247.71},
        {'date': '25 Sep', 'value': 73895.74, 'change': +315.20},
    ]


@app.route('/')
def home():
  return redirect(url_for('admin_login'))


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
  if request.method == 'POST':
    mobile = request.form.get('mobile', '').strip()
    password = request.form.get('password', '').strip()

    if mobile == '+918078535666' and password == 'Bichu@5419':
      session.permanent = True
      session['is_admin'] = True
      return redirect(url_for('admin_dashboard'))
    else:
      flash('Invalid Credentials', 'danger')

  return render_template('admin_login.html')


@app.route('/admin-dashboard')
def admin_dashboard():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))

  try:
    archive_files = os.listdir(app.config['UPLOAD_FOLDER'])
  except:
    archive_files = []

  return render_template(
      'admin_dashboard.html',
      admin_name=ADMIN_NAME,
      sensex_trend=get_recent_sensex(),
      users=REGISTERED_USERS,
      feedback=USER_FEEDBACK,
      equity_data=parse_fund_excel('equity_funds.xlsx'),
      balancer_data=parse_fund_excel('balancer_funds.xlsx'),
      debt_data=parse_fund_excel('debt_funds.xlsx'),
      archive_files=archive_files,
  )


@app.route('/user-dashboard')
def user_dashboard():
  try:
    archive_files = os.listdir(app.config['UPLOAD_FOLDER'])
  except:
    archive_files = []
  return render_template(
      'user_dashboard.html',
      sensex_trend=get_recent_sensex(),
      equity_data=parse_fund_excel('equity_funds.xlsx'),
      balancer_data=parse_fund_excel('balancer_funds.xlsx'),
      debt_data=parse_fund_excel('debt_funds.xlsx'),
      archive_files=archive_files,
  )


@app.route('/download-latest-nav')
def download_latest_nav():
  try:
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    image_files = [
        f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    if image_files:
      latest_image = max(
          image_files,
          key=lambda x: os.path.getctime(
              os.path.join(app.config['UPLOAD_FOLDER'], x)
          ),
      )
      return send_from_directory(
          app.config['UPLOAD_FOLDER'], latest_image, as_attachment=True
      )
  except Exception as e:
    print(f'Error downloading latest nav: {e}')
  flash('No NAV image found to download.', 'warning')
  return redirect(url_for('admin_dashboard'))


@app.route('/update-user-status/<int:user_id>/<status>', methods=['POST'])
def update_user_status(user_id, status):
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  for user in REGISTERED_USERS:
    if user['id'] == user_id:
      user['status'] = status.capitalize()
  return redirect(url_for('admin_dashboard'))


@app.route('/upload-master-category', methods=['POST'])
def upload_master_category():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  category = request.form.get('category')  # equity, balancer, or debt
  file_key = f'{category}_file'
  if file_key in request.files:
    file = request.files[file_key]
    if file.filename != '':
      filename = f'{category}_funds.xlsx'
      file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
  return redirect(url_for('admin_dashboard'))


@app.route('/upload-nav', methods=['POST'])
def upload_nav():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  if 'nav_image' in request.files:
    file = request.files['nav_image']
    if file.filename != '':
      filename = secure_filename(file.filename)
      file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
  return redirect(url_for('admin_dashboard'))


@app.route('/upload-bulk-nav', methods=['POST'])
def upload_bulk_nav():
  if not session.get('is_admin'):
    return redirect(url_for('admin_login'))
  if 'bulk_images' in request.files:
    files = request.files.getlist('bulk_images')
    for file in files:
      if file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
  return redirect(url_for('admin_dashboard'))


@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
  name = request.form.get('name', 'Anonymous')
  message = request.form.get('message', '')
  if message:
    USER_FEEDBACK.insert(
        0,
        {
            'name': name,
            'message': message,
            'date': datetime.now().strftime('%d %b %Y'),
        },
    )
  return redirect(url_for('user_dashboard'))


@app.errorhandler(500)
def internal_server_error(e):
  print('SERVER ERROR:', traceback.format_exc())
  return (
      f'<h3>Internal Server Error Details:</h3><pre>{traceback.format_exc()}</pre>',
      500,
  )


if __name__ == '__main__':
  app.run(debug=True)