os = __import__('os')
import pandas as pd
import yfinance as yf
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'nav_updates_secret_key'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory user database simulation for approvals
REGISTERED_USERS = [
    {'id': 1, 'name': 'Rahul Sharma', 'mobile': '+91 9876543210', 'status': 'Pending'},
    {'id': 2, 'name': 'Priya Nair', 'mobile': '+91 9876522888', 'status': 'Approved'}
]

def get_recent_sensex():
    try:
        sensex = yf.Ticker("^BSESN")
        df = sensex.history(period="10d")
        recent_5 = df.tail(5)
        
        trend_data = []
        prev_close = None
        
        for index, row in recent_5.iterrows():
            date_str = index.strftime('%d %b')
            close_val = round(row['Close'], 2)
            
            change_pct = 0.0
            if prev_close is not None:
                change_pct = round(((close_val - prev_close) / prev_close) * 100, 2)
            
            trend_data.append({
                'date': date_str,
                'value': close_val,
                'change': change_pct
            })
            prev_close = close_val
            
        return trend_data
    except Exception as e:
        print(f"Error fetching Sensex data: {e}")
        return [
            {'date': '17 Sep', 'value': 74314.59, 'change': 0.0},
            {'date': '18 Sep', 'value': 74294.96, 'change': -0.03},
            {'date': '21 Sep', 'value': 74858.99, 'change': 0.76},
            {'date': '23 Sep', 'value': 74828.25, 'change': -0.04},
            {'date': '24 Sep', 'value': 73580.54, 'change': -1.67},
        ]

def format_pct(val):
    try:
        f = float(val)
        return round(f * 100, 2)
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
                if val and val.lower() != 'nan' and val.lower() != 'funds':
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
            session['username'] = username
            session['mobile'] = mobile
            # Register user if not already in list
            if not any(u['mobile'] == mobile for u in REGISTERED_USERS):
                REGISTERED_USERS.append({
                    'id': len(REGISTERED_USERS) + 1,
                    'name': username,
                    'mobile': mobile,
                    'status': 'Pending'
                })
            return redirect(url_for('user_dashboard'))
    return render_template('login.html')

@app.route('/user-dashboard')
def user_dashboard():
    username = session.get('username', 'Client')
    mobile = session.get('mobile', '')
    sensex_trend = get_recent_sensex()
    equity_data = parse_fund_excel('equity_funds.xlsx')
    balancer_data = parse_fund_excel('balancer_funds.xlsx')
    debt_data = parse_fund_excel('debt_funds.xlsx')

    return render_template(
        'user_dashboard.html',
        username=username,
        mobile=mobile,
        sensex_trend=sensex_trend,
        equity_data=equity_data,
        balancer_data=balancer_data,
        debt_data=debt_data
    )

@app.route('/admin-dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    sensex_trend = get_recent_sensex()
    equity_data = parse_fund_excel('equity_funds.xlsx')
    balancer_data = parse_fund_excel('balancer_funds.xlsx')
    debt_data = parse_fund_excel('debt_funds.xlsx')

    return render_template(
        'admin_dashboard.html',
        sensex_trend=sensex_trend,
        users=REGISTERED_USERS,
        equity_data=equity_data,
        balancer_data=balancer_data,
        debt_data=debt_data
    )

@app.route('/update-user-status/<int:user_id>/<status>', methods=['POST'])
def update_user_status(user_id, status):
    for user in REGISTERED_USERS:
        if user['id'] == user_id:
            user['status'] = status.capitalize()
    return redirect(url_for('admin_dashboard'))

@app.route('/upload-master-category', methods=['POST'])
def upload_master_category():
    category = request.form.get('category')
    file_key = f'{category}_file'
    if file_key in request.files:
        file = request.files[file_key]
        if file.filename != '':
            filename = f'{category}_funds.xlsx'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash(f'{category.capitalize()} funds excel updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/upload-nav', methods=['POST'])
def upload_nav():
    if 'nav_image' in request.files:
        file = request.files['nav_image']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('NAV Image uploaded successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/upload-archive', methods=['POST'])
def upload_archive():
    files = request.files.getlist('archive_files')
    for file in files:
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    flash('Archive files uploaded successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)