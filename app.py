import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'nav_updates_secret_key'
app.permanent_session_lifetime = timedelta(days=30)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

REGISTERED_USERS = [
    {'id': 1, 'name': 'Rahul Sharma', 'mobile': '+91 9876543210', 'status': 'Pending', 'approved_at': None},
    {'id': 2, 'name': 'Priya Nair', 'mobile': '+91 9876522888', 'status': 'Approved', 'approved_at': datetime.now().isoformat()}
]

def check_user_validity(user):
    if user['status'] == 'Approved' and user.get('approved_at'):
        approved_date = datetime.fromisoformat(user['approved_at'])
        if datetime.now() - approved_date > timedelta(days=30):
            user['status'] = 'Pending'
            user['approved_at'] = None

def get_recent_sensex():
    try:
        sensex = yf.Ticker("^BSESN")
        df = sensex.history(period="10d")
        if df.empty:
            raise ValueError("Empty dataframe")
        recent_5 = df.tail(5)
        
        trend_data = []
        prev_close = None
        
        for index, row in recent_5.iterrows():
            date_str = index.strftime('%d %b')
            close_val = round(row['Close'], 2)
            change_pct = round(((close_val - prev_close) / prev_close) * 100, 2) if prev_close else 0.0
            trend_data.append({'date': date_str, 'value': close_val, 'change': change_pct})
            prev_close = close_val
        return trend_data
    except Exception as e:
        print(f"Error fetching Sensex data: {e}")
        return [
            {'date': '21 Sep', 'value': 74858.99, 'change': 0.0},
            {'date': '22 Sep', 'value': 74528.08, 'change': -0.44},
            {'date': '23 Sep', 'value': 74828.25, 'change': 0.4},
            {'date': '24 Sep', 'value': 73580.54, 'change': -1.67},
            {'date': '25 Sep', 'value': 73895.74, 'change': 0.43},
        ]

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
                        "fund": val,
                        "inception": str(row.iloc[1]) if len(row) > 1 else "",
                        "benchmark": str(row.iloc[2]) if len(row) > 2 else "",
                        "since": format_pct(row.iloc[3]) if len(row) > 3 else "0",
                        "m1": format_pct(row.iloc[4]) if len(row) > 4 else "0",
                        "m6": format_pct(row.iloc[5]) if len(row) > 5 else "0",
                        "y1": format_pct(row.iloc[6]) if len(row) > 6 else "0",
                        "y2": format_pct(row.iloc[7]) if len(row) > 7 else "0",
                        "y3": format_pct(row.iloc[8]) if len(row) > 8 else "0",
                        "y4": format_pct(row.iloc[9]) if len(row) > 9 else "0",
                        "y5": format_pct(row.iloc[10]) if len(row) > 10 else "0",
                        "y7": format_pct(row.iloc[11]) if len(row) > 11 else "0",
                        "y10": format_pct(row.iloc[12]) if len(row) > 12 else "0",
                        "high": str(row.iloc[13]) if len(row) > 13 else "0",
                        "latest": str(row.iloc[14]) if len(row) > 14 else "0"
                    })
        except Exception as e:
            print(f"Error reading {filename}: {e}")
    return fund_list

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
            
            user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
            if not user_record:
                user_record = {
                    'id': len(REGISTERED_USERS) + 1,
                    'name': username,
                    'mobile': mobile,
                    'status': 'Pending',
                    'approved_at': None
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
    user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
    
    if user_record and user_record['status'] == 'Approved':
        return redirect(url_for('user_dashboard'))
        
    return render_template('pending_approval.html', username=session.get('username', 'User'))

@app.route('/user-dashboard')
def user_dashboard():
    mobile = session.get('mobile', '')
    user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
    
    if user_record:
        check_user_validity(user_record)
        if user_record['status'] == 'Pending':
            return redirect(url_for('pending_approval'))
            
    if not user_record:
        return redirect(url_for('login'))

    return render_template(
        'user_dashboard.html',
        username=session.get('username', 'Client'),
        mobile=mobile,
        sensex_trend=get_recent_sensex(),
        equity_data=parse_fund_excel('equity_funds.xlsx'),
        balancer_data=parse_fund_excel('balancer_funds.xlsx'),
        debt_data=parse_fund_excel('debt_funds.xlsx')
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
        
    return render_template(
        'admin_dashboard.html',
        sensex_trend=get_recent_sensex(),
        users=REGISTERED_USERS,
        equity_data=parse_fund_excel('equity_funds.xlsx'),
        balancer_data=parse_fund_excel('balancer_funds.xlsx'),
        debt_data=parse_fund_excel('debt_funds.xlsx'),
        current_time=datetime.now().strftime('%b %d, %Y, %I:%M:%S %p')
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

@app.route('/upload-master-category', methods=['POST'])
def upload_master_category():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    category = request.form.get('category')
    file_key = f'{category}_file'
    if file_key in request.files:
        file = request.files[file_key]
        if file.filename != '':
            filename = f'{category}_funds.xlsx'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash(f'{category.capitalize()} funds updated successfully!', 'success')
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
            flash('NAV Image uploaded successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/upload-archive', methods=['POST'])
def upload_archive():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    for file in request.files.getlist('archive_files'):
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    flash('Archive files uploaded successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)