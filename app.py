import os
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'nav_update_secret_key_bijoosh_secure'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
OLD_NAV_FOLDER = os.path.join('static', 'old_nav')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OLD_NAV_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OLD_NAV_FOLDER'] = OLD_NAV_FOLDER

ADMIN_CREDENTIALS = {'username': '+918078535666', 'password': 'Bichu@5419'}

VISITOR_LOGS = [
    {'id': 1, 'mobile': '+91 9876543210', 'action': 'Requested Login Access', 'status': 'Pending', 'timestamp': '18 Sep 2026, 09:30 AM'},
    {'id': 2, 'mobile': '+91 9123456789', 'action': 'Viewed Equity Funds', 'status': 'Approved', 'timestamp': '18 Sep 2026, 10:15 AM'}
]

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        mobile = request.form.get('mobile', '+918078535666')
        
        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            session['user'] = username
            session['mobile'] = mobile
            VISITOR_LOGS.insert(0, {'id': len(VISITOR_LOGS)+1, 'mobile': mobile, 'action': 'Admin Login & Dashboard Access', 'status': 'Approved', 'timestamp': datetime.now().strftime('%d %b %Y, %H:%M %p')})
            return redirect(url_for('dashboard'))
        else:
            VISITOR_LOGS.insert(0, {'id': len(VISITOR_LOGS)+1, 'mobile': username, 'action': 'User Login Request', 'status': 'Pending', 'timestamp': datetime.now().strftime('%d %b %Y, %H:%M %p')})
            flash('Login request sent to Admin for approval.', 'warning')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('mobile', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    equity_funds = []
    balanced_funds = []
    debt_funds = []
    
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'master_fund.xlsx')
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            current_category = "Equity"

            for i, row in df.iterrows():
                f_col = str(row.iloc[0]).strip().upper()
                if 'BALANCED' in f_col:
                    current_category = "Balanced"
                    continue
                elif 'DEBT' in f_col:
                    current_category = "Debt"
                    continue
                
                fund_name = row.iloc[1]
                if pd.isna(fund_name) or str(fund_name).strip() == '' or 'FUNDS' in str(fund_name).upper() or 'E Q U I T Y' in str(fund_name).upper():
                    continue

                f_name_str = str(fund_name).strip()
                
                try:
                    nav_val = row.iloc[-1]
                    latest_nav = float(nav_val) if pd.notna(nav_val) else 10.0
                except:
                    latest_nav = 10.0

                fund = {
                    'name': f_name_str,
                    'category': current_category.lower(),
                    'inception_date': str(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else '-',
                    'benchmark': str(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else '-',
                    'since_inception': str(row.iloc[4]) if len(row) > 4 and pd.notna(row.iloc[4]) else '-',
                    'm1': str(row.iloc[5]) if len(row) > 5 and pd.notna(row.iloc[5]) else '-',
                    'm6': str(row.iloc[6]) if len(row) > 6 and pd.notna(row.iloc[6]) else '-',
                    'y1': str(row.iloc[7]) if len(row) > 7 and pd.notna(row.iloc[7]) else '-',
                    'y2': str(row.iloc[8]) if len(row) > 8 and pd.notna(row.iloc[8]) else '-',
                    'y3': str(row.iloc[9]) if len(row) > 9 and pd.notna(row.iloc[9]) else '-',
                    'y4': str(row.iloc[10]) if len(row) > 10 and pd.notna(row.iloc[10]) else '-',
                    'y5': str(row.iloc[11]) if len(row) > 11 and pd.notna(row.iloc[11]) else '-',
                    'y7': str(row.iloc[12]) if len(row) > 12 and pd.notna(row.iloc[12]) else '-',
                    'y10': str(row.iloc[13]) if len(row) > 13 and pd.notna(row.iloc[13]) else '-',
                    'highest_value': str(row.iloc[14]) if len(row) > 14 and pd.notna(row.iloc[14]) else '-',
                    'latest_nav': latest_nav,
                    'is_above_base': latest_nav >= 10.0
                }

                if current_category == "Equity":
                    equity_funds.append(fund)
                elif current_category == "Balanced":
                    balanced_funds.append(fund)
                elif current_category == "Debt":
                    debt_funds.append(fund)
        except Exception as e:
            print(f"Error reading Excel: {e}")

    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    current_year = datetime.now().year
    old_nav_archive = {yr: months for yr in range(2024, current_year + 1)}

    nav_image = None
    uploads = os.listdir(app.config['UPLOAD_FOLDER'])
    image_files = [f for f in uploads if f.lower().endswith(('.png', '.jpg', '.jpeg')) and f != 'master_fund.xlsx']
    if image_files:
        image_files.sort(key=lambda x: os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], x)), reverse=True)
        nav_image = image_files[0]

    sensex_data = {
        'current': '74421.04',
        'change': '+106.45',
        'is_up': True,
        'time': datetime.now().strftime('%d %b %Y, %H:%M:%S'),
        'history': [
            {'date': '14 Sep', 'value': '74781.76', 'change': '-120.63', 'is_up': False},
            {'date': '15 Sep', 'value': '74003.82', 'change': '-777.94', 'is_up': False},
            {'date': '16 Sep', 'value': '74336.45', 'change': '+332.63', 'is_up': True},
            {'date': '17 Sep', 'value': '74314.59', 'change': '-21.86', 'is_up': False},
            {'date': '18 Sep', 'value': '74421.04', 'change': '+106.45', 'is_up': True}
        ]
    }

    return render_template(
        'dashboard.html',
        equity_funds=equity_funds,
        balanced_funds=balanced_funds,
        debt_funds=debt_funds,
        old_nav_archive=old_nav_archive,
        nav_image=nav_image,
        sensex=sensex_data,
        admin_name="BIJOOSH PADMAKUMAR",
        visitors=VISITOR_LOGS
    )

@app.route('/user_dashboard')
def user_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    equity_funds = []
    balanced_funds = []
    debt_funds = []
    
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'master_fund.xlsx')
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            current_category = "Equity"

            for i, row in df.iterrows():
                f_col = str(row.iloc[0]).strip().upper()
                if 'BALANCED' in f_col:
                    current_category = "Balanced"
                    continue
                elif 'DEBT' in f_col:
                    current_category = "Debt"
                    continue
                
                fund_name = row.iloc[1]
                if pd.isna(fund_name) or str(fund_name).strip() == '' or 'FUNDS' in str(fund_name).upper() or 'E Q U I T Y' in str(fund_name).upper():
                    continue

                f_name_str = str(fund_name).strip()
                try:
                    nav_val = row.iloc[-1]
                    latest_nav = float(nav_val) if pd.notna(nav_val) else 10.0
                except:
                    latest_nav = 10.0

                fund = {
                    'name': f_name_str,
                    'category': current_category.lower(),
                    'inception_date': str(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else '-',
                    'benchmark': str(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else '-',
                    'since_inception': str(row.iloc[4]) if len(row) > 4 and pd.notna(row.iloc[4]) else '-',
                    'm1': str(row.iloc[5]) if len(row) > 5 and pd.notna(row.iloc[5]) else '-',
                    'm6': str(row.iloc[6]) if len(row) > 6 and pd.notna(row.iloc[6]) else '-',
                    'y1': str(row.iloc[7]) if len(row) > 7 and pd.notna(row.iloc[7]) else '-',
                    'y2': str(row.iloc[8]) if len(row) > 8 and pd.notna(row.iloc[8]) else '-',
                    'y3': str(row.iloc[9]) if len(row) > 9 and pd.notna(row.iloc[9]) else '-',
                    'y4': str(row.iloc[10]) if len(row) > 10 and pd.notna(row.iloc[10]) else '-',
                    'y5': str(row.iloc[11]) if len(row) > 11 and pd.notna(row.iloc[11]) else '-',
                    'y7': str(row.iloc[12]) if len(row) > 12 and pd.notna(row.iloc[12]) else '-',
                    'y10': str(row.iloc[13]) if len(row) > 13 and pd.notna(row.iloc[13]) else '-',
                    'highest_value': str(row.iloc[14]) if len(row) > 14 and pd.notna(row.iloc[14]) else '-',
                    'latest_nav': latest_nav,
                    'is_above_base': latest_nav >= 10.0
                }

                if current_category == "Equity":
                    equity_funds.append(fund)
                elif current_category == "Balanced":
                    balanced_funds.append(fund)
                elif current_category == "Debt":
                    debt_funds.append(fund)
        except Exception as e:
            print(f"Error reading Excel: {e}")

    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    current_year = datetime.now().year
    old_nav_archive = {yr: months for yr in range(2024, current_year + 1)}

    nav_image = None
    uploads = os.listdir(app.config['UPLOAD_FOLDER'])
    image_files = [f for f in uploads if f.lower().endswith(('.png', '.jpg', '.jpeg')) and f != 'master_fund.xlsx']
    if image_files:
        image_files.sort(key=lambda x: os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], x)), reverse=True)
        nav_image = image_files[0]

    sensex_data = {
        'current': '74421.04',
        'change': '+106.45',
        'is_up': True,
        'time': datetime.now().strftime('%d %b %Y, %H:%M:%S'),
        'history': [
            {'date': '14 Sep', 'value': '74781.76', 'change': '-120.63', 'is_up': False},
            {'date': '15 Sep', 'value': '74003.82', 'change': '-777.94', 'is_up': False},
            {'date': '16 Sep', 'value': '74336.45', 'change': '+332.63', 'is_up': True},
            {'date': '17 Sep', 'value': '74314.59', 'change': '-21.86', 'is_up': False},
            {'date': '18 Sep', 'value': '74421.04', 'change': '+106.45', 'is_up': True}
        ]
    }

    return render_template(
        'user_dashboard.html',
        equity_funds=equity_funds,
        balanced_funds=balanced_funds,
        debt_funds=debt_funds,
        old_nav_archive=old_nav_archive,
        nav_image=nav_image,
        sensex=sensex_data,
        admin_name="BIJOOSH PADMAKUMAR"
    )

@app.route('/admin/upload_excel', methods=['POST'])
def upload_excel():
    if 'user' not in session:
        return redirect(url_for('login'))
    if 'master_excel' in request.files:
        file = request.files['master_excel']
        if file.filename != '':
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'master_fund.xlsx'))
            flash('Master fund excel uploaded & updated successfully across dashboards!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/upload_old_nav', methods=['POST'])
def upload_old_nav():
    if 'user' not in session:
        return redirect(url_for('login'))
    year = request.form.get('nav_year')
    month = request.form.get('nav_month')
    
    uploaded_files = request.files.getlist('old_nav_file')
    count = 0
    for file in uploaded_files:
        if file and file.filename != '':
            filename = secure_filename(f"{year}_{month}_{file.filename}")
            file.save(os.path.join(app.config['OLD_NAV_FOLDER'], filename))
            count += 1
            
    if count > 0:
        flash(f'{count} Old NAV file(s) for {month} {year} uploaded successfully!', 'success')
    else:
        flash('No files selected for upload.', 'danger')
        
    return redirect(url_for('dashboard'))

@app.route('/admin/upload_today_nav', methods=['POST'])
def upload_today_nav():
    if 'user' not in session:
        return redirect(url_for('login'))
    if 'nav_image' in request.files:
        file = request.files['nav_image']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash("Today's NAV JPEG image uploaded successfully!", 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/approve_user/<int:log_id>', methods=['POST'])
def approve_user(log_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    for v in VISITOR_LOGS:
        if v['id'] == log_id:
            v['status'] = 'Approved'
            flash(f"Login access approved for {v['mobile']}.", 'success')
            break
    return redirect(url_for('dashboard'))

@app.route('/admin/reject_user/<int:log_id>', methods=['POST'])
def reject_user(log_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    for v in VISITOR_LOGS:
        if v['id'] == log_id:
            v['status'] = 'Rejected'
            flash(f"Login access rejected for {v['mobile']}.", 'danger')
            break
    return redirect(url_for('dashboard'))

@app.route('/track_action', methods=['POST'])
def track_action():
    action_type = request.form.get('action')
    mobile = session.get('mobile', 'Guest User')
    VISITOR_LOGS.insert(0, {'id': len(VISITOR_LOGS)+1, 'mobile': mobile, 'action': action_type, 'status': 'Approved', 'timestamp': datetime.now().strftime('%d %b %Y, %H:%M %p')})
    return '', 204

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    flash('Thank you for your feedback and suggestion!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
