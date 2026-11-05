from datetime import datetime, timedelta, timezone
import json
import os
import random
import re
import urllib.parse
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
    default_limits=["10000 per day", "1000 per hour"],
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
ADMIN_MOBILE = "+918078535666"

REGISTERED_USERS = [
    {
        'id': 1,
        'name': 'Rahul Sharma',
        'mobile': '+91 9876543210',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(minutes=15),
        'approved_at': datetime.now().isoformat(),
        'last_login': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
        'last_active': datetime.now()
    },
    {
        'id': 2,
        'name': 'Priya Nair',
        'mobile': '+91 9876522888',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(days=5),
        'approved_at': datetime.now().isoformat(),
        'last_login': (datetime.now() - timedelta(hours=2)).strftime('%b %d, %Y, %I:%M %p'),
        'last_active': datetime.now() - timedelta(minutes=10)
    },
    {
        'id': 3,
        'name': 'biju',
        'mobile': '+917034788666',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(days=10),
        'approved_at': datetime.now().isoformat(),
        'last_login': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
        'last_active': datetime.now()
    },
]

USER_FEEDBACKS = [
    {
        'id': 1,
        'username': 'Rahul Sharma',
        'feedback': 'Great portal! Very intuitive and fast NAV updates. (Rating: 5★)',
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    },
]

DOWNLOAD_REQUESTS = [
    {
        'id': 1,
        'username': 'Rahul Sharma',
        'filename': 'latest_nav.jpg',
        'type': 'download',
        'status': 'Pending',
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
        'approved_at': None
    }
]

CHAT_MESSAGES = []
PENDING_OTPS = {}


def send_whatsapp_admin_alert(message_text):
    encoded_msg = urllib.parse.quote(message_text)
    url = f"https://api.callmebot.com/whatsapp.php?phone={ADMIN_MOBILE}&text={encoded_msg}&apikey=FREE_GATEWAY"
    try:
        requests.get(url, timeout=3)
    except Exception as e:
        print(f"[WhatsApp Alert Error]: {e}")


def check_user_validity(user):
    if not ADMIN_SETTINGS.get('auto_approval_enabled', True):
        return
    now = datetime.now()
    if user['status'] == 'Pending':
        reg_time = user.get('registered_at', now)
        if now - reg_time > timedelta(minutes=5):
            user['status'] = 'Approved'
            user['approved_at'] = now.isoformat()


@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    if 'username' in session:
        uname = session.get('username')
        for u in REGISTERED_USERS:
            if u['name'] == uname:
                u['last_active'] = datetime.now()
                break
    elif session.get('is_admin'):
        ADMIN_ACTIVITY['last_active'] = datetime.now()
    return jsonify({'success': True})


@app.route('/api/send-message', methods=['POST'])
def send_message():
    if 'username' not in session and not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    data = request.get_json() or {}
    msg_text = data.get('message', '').strip()
    recipient = data.get('recipient', 'Admin')
    sender = session.get('username') if 'username' in session else 'Admin Bijoosh'

    if msg_text:
        CHAT_MESSAGES.append({
            'id': len(CHAT_MESSAGES) + 1,
            'sender': sender,
            'recipient': recipient,
            'message': msg_text,
            'timestamp': datetime.now().strftime('%I:%M %p')
        })
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Empty message'})


@app.route('/api/get-messages', methods=['GET'])
def get_messages():
    if 'username' not in session and not session.get('is_admin'):
        return jsonify({'success': False, 'messages': []})
    return jsonify({'success': True, 'messages': CHAT_MESSAGES})


CACHE_FILE = 'market_cache.json'
DEFAULT_MARKET_CACHE = {
    'nifty50': {'value': '23,960.60', 'change': '+519.80 pts (+2.22%)', 'is_positive': True},
    'sensex': {'value': '77,301.40', 'change': '+383.55 pts (+0.50%)', 'is_positive': True},
    'nifty500': {'value': '22,769.20', 'change': '+527.80 pts (+2.37%)', 'is_positive': True},
    'trend_data': [
        {'date': '29 Oct', 'nifty50': '22,936.75', 'sensex': '74,151.04', 'nifty500': '21,790.30', 'change': 905.01},
        {'date': '30 Oct', 'nifty50': '23,053.10', 'sensex': '74,459.53', 'nifty500': '21,895.90', 'change': 308.49},
        {'date': '02 Nov', 'nifty50': '23,440.80', 'sensex': '75,692.78', 'nifty500': '22,241.40', 'change': 1233.25},
        {'date': '03 Nov', 'nifty50': '23,810.85', 'sensex': '76,917.85', 'nifty500': '22,520.35', 'change': 1225.07},
        {'date': '04 Nov', 'nifty50': '23,960.60', 'sensex': '77,301.40', 'nifty500': '22,769.20', 'change': 383.55},
    ]
}


def load_market_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_MARKET_CACHE.copy()


def get_live_market_data():
    cache = load_market_cache()
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    is_weekend = ist_now.weekday() >= 5
    is_market_hours = (not is_weekend) and (9 <= ist_now.hour < 16 or (ist_now.hour == 16 and ist_now.minute == 0))

    indices = {'nifty50': '^NSEI', 'sensex': '^BSESN', 'nifty500': '^CRSLDX'}
    result = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for key, ticker in indices.items():
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                res_json = response.json()
                meta = res_json['chart']['result'][0]['meta']
                ltp = float(meta.get('regularMarketPrice', 0))
                prev_close = float(meta.get('chartPreviousClose', ltp))
                if ltp > 0:
                    change = ltp - prev_close
                    pct_change = (change / prev_close) * 100 if prev_close else 0
                    result[key] = {'value': f"{ltp:,.2f}", 'change': f"{change:+,.2f} pts ({pct_change:+.2f}%)", 'is_positive': change >= 0}
        except Exception:
            pass

        if key not in result:
            cached_item = cache.get(key, {})
            result[key] = {'value': cached_item.get('value', '0.00'), 'change': cached_item.get('change', '+0.00 pts (0.00%)'), 'is_positive': cached_item.get('is_positive', True)}

    time_label = f"CLOSED | As on 04:00 PM | {ist_now.strftime('%d %b %Y')}" if not is_market_hours else f"Live as of: {ist_now.strftime('%b %d, %Y, %I:%M:%S %p')}"
    return {'nifty50': result['nifty50'], 'sensex': result['sensex'], 'nifty500': result['nifty500'], 'time_label': time_label, 'is_market_open': is_market_hours}, cache.get('trend_data', [])


@app.route('/api/market-live')
@limiter.exempt
def market_live():
    market_info, _ = get_live_market_data()
    return jsonify(market_info)


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
    except Exception:
        pass
    return fund_list


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
        step = request.form.get('step', 'request_code')
        username = request.form.get('username', '').strip()
        mobile = request.form.get('mobile', '').strip()

        name_is_valid = bool(re.match(r'^[A-Za-z\s]+$', username))
        clean_mobile = re.sub(r'\D', '', mobile)
        mobile_is_valid = 10 <= len(clean_mobile) <= 12

        if not name_is_valid or not mobile_is_valid:
            flash('Use correct name (letters only) and valid mobile number.', 'danger')
            return render_template('login.html', step='request_code', display_code='')

        if step == 'request_code':
            display_code = str(random.randint(1000, 9999))
            PENDING_OTPS[mobile] = display_code
            return render_template('login.html', step='verify_code', username=username, mobile=mobile, display_code=display_code)

        elif step == 'verify_code':
            entered_code = request.form.get('code', '').strip()
            display_code = request.form.get('display_code', '').strip()
            if mobile in PENDING_OTPS and PENDING_OTPS[mobile] == entered_code:
                del PENDING_OTPS[mobile]
                session.permanent = True
                session['username'] = username
                session['mobile'] = mobile
                user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
                login_time_str = datetime.now().strftime('%b %d, %Y, %I:%M %p')
                if not user_record:
                    user_record = {
                        'id': len(REGISTERED_USERS) + 1,
                        'name': username,
                        'mobile': mobile,
                        'status': 'Pending',
                        'registered_at': datetime.now(),
                        'approved_at': None,
                        'last_login': login_time_str,
                        'last_active': datetime.now()
                    }
                    REGISTERED_USERS.append(user_record)
                else:
                    user_record['last_login'] = login_time_str
                    user_record['last_active'] = datetime.now()
                    check_user_validity(user_record)

                if user_record['status'] == 'Pending':
                    return redirect(url_for('pending_approval'))
                return redirect(url_for('user_dashboard'))
            else:
                flash('Invalid code entered. Please type the correct displayed code.', 'danger')
                return render_template('login.html', step='verify_code', username=username, mobile=mobile, display_code=display_code)

    return render_template('login.html', step='request_code', display_code='')


@app.route('/pending-approval')
def pending_approval():
    mobile = session.get('mobile', '')
    user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
    if user_record:
        check_user_validity(user_record)
        if user_record['status'] == 'Approved':
            return redirect(url_for('user_dashboard'))
    return render_template('pending_approval.html', username=session.get('username', 'User'))


@app.route('/check-approval-status')
def check_approval_status():
    mobile = session.get('mobile', '')
    user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
    if user_record:
        check_user_validity(user_record)
        if user_record['status'] == 'Approved':
            return "APPROVED"
    return "PENDING"


@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    if 'username' not in session:
        return redirect(url_for('login'))
    feedback_text = request.form.get('feedback', '').strip()
    rating = request.form.get('rating', '5')
    username = session.get('username')
    if feedback_text:
        USER_FEEDBACKS.append({
            'id': len(USER_FEEDBACKS) + 1,
            'username': username,
            'feedback': f"{feedback_text} (Rating: {rating}★)",
            'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p')
        })
        flash('Feedback submitted successfully!', 'success')
    return redirect(url_for('user_dashboard'))


@app.route('/user-dashboard')
def user_dashboard():
    try:
        mobile = session.get('mobile', '')
        uname = session.get('username', '')
        user_record = next((u for u in REGISTERED_USERS if u['mobile'] == mobile), None)
        if user_record:
            user_record['last_active'] = datetime.now()
            check_user_validity(user_record)
            if user_record['status'] == 'Pending':
                return redirect(url_for('pending_approval'))
        if not user_record:
            return redirect(url_for('login'))

        market_info, market_trend_data = get_live_market_data()
        admin_online = (datetime.now() - ADMIN_ACTIVITY['last_active']) < timedelta(minutes=2)
        festival_greeting = None

        latest_filename = 'latest_nav.jpg'
        try:
            meta_path = os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json')
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as mf:
                    meta = json.load(mf)
                    latest_filename = meta.get('filename', 'latest_nav.jpg')
        except Exception:
            pass

        user_requests = [r for r in DOWNLOAD_REQUESTS if r['username'] == uname]

        can_download_latest = False
        latest_req = next((r for r in user_requests if r['filename'] == latest_filename and r['status'] == 'Approved' and r.get('approved_at')), None)
        if latest_req:
            appr_time = datetime.fromisoformat(latest_req['approved_at'])
            if datetime.now() - appr_time <= timedelta(minutes=5):
                can_download_latest = True

        return render_template(
            'user_dashboard.html',
            username=uname,
            mobile=mobile,
            market=market_info,
            market_trend=market_trend_data,
            equity_data=parse_fund_excel_from_db('equity_funds'),
            balancer_data=parse_fund_excel_from_db('balancer_funds'),
            debt_data=parse_fund_excel_from_db('debt_funds'),
            admin_online=admin_online,
            admin_mobile=ADMIN_MOBILE,
            festival_greeting=festival_greeting,
            download_requests=user_requests,
            latest_filename=latest_filename,
            can_download_latest=can_download_latest
        )
    except Exception:
        return redirect(url_for('login'))


@app.route('/request-download', methods=['POST'])
def request_download():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    data = request.get_json() or {}
    file_name = data.get('filename', 'latest_nav.jpg')
    download_type = data.get('type', 'download')
    username = session.get('username')

    existing = next((r for r in DOWNLOAD_REQUESTS if r['username'] == username and r['filename'] == file_name and r['status'] == 'Pending'), None)
    if not existing:
        req_id = len(DOWNLOAD_REQUESTS) + 1
        DOWNLOAD_REQUESTS.append({
            'id': req_id,
            'username': username,
            'filename': file_name,
            'type': download_type,
            'status': 'Pending',
            'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
            'approved_at': None
        })
        send_whatsapp_admin_alert(f"🚨 *NAV Download Request*\n\n*User:* {username}\n*File:* {file_name}\n\n⚡ Open your Admin Dashboard to approve.")

    return jsonify({'success': True, 'message': 'Approval request sent to Admin successfully.'})


@app.route('/get-nav-image-base64/<path:filename>')
def get_nav_image_base64(filename):
    if 'username' not in session and not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(target_path):
        for root, dirs, files in os.walk(ARCHIVE_FOLDER):
            if filename in files:
                target_path = os.path.join(root, filename)
                break

    if os.path.exists(target_path):
        import base64
        with open(target_path, 'rb') as img_f:
            b64_data = base64.b64encode(img_f.read()).decode('utf-8')
        return jsonify({'success': True, 'image_data': f"data:image/jpeg;base64,{b64_data}"})
    return jsonify({'success': False, 'message': 'Image not found'})


@app.route('/view-archive-secured/<path:filename>')
def view_archive_secured(filename):
    if 'username' not in session and not session.get('is_admin'):
        return redirect(url_for('login'))
    
    if session.get('is_admin'):
        for root, dirs, files in os.walk(ARCHIVE_FOLDER):
            if filename in files:
                return send_from_directory(root, filename)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    uname = session.get('username')
    approved_req = next((r for r in DOWNLOAD_REQUESTS if r['username'] == uname and r['filename'] == filename and r['status'] == 'Approved' and r.get('approved_at')), None)
    
    if approved_req:
        appr_time = datetime.fromisoformat(approved_req['approved_at'])
        if datetime.now() - appr_time <= timedelta(minutes=5):
            for root, dirs, files in os.walk(ARCHIVE_FOLDER):
                if filename in files:
                    return send_from_directory(root, filename)
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        else:
            flash('Download window expired (5 minutes exceeded). Request approval again.', 'danger')
    else:
        flash('Download requires Admin Approval or request expired.', 'warning')
    return redirect(url_for('user_dashboard'))


@app.route('/admin-login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
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

    market_info, market_trend_data = get_live_market_data()
    user_filter = request.args.get('user_filter', 'all')
    req_filter = request.args.get('req_filter', 'all')

    formatted_users = []
    for u in REGISTERED_USERS:
        u_copy = u.copy()
        last_act = u.get('last_active')
        is_online = last_act and (datetime.now() - last_act) < timedelta(minutes=2)
        u_copy['is_online'] = is_online
        formatted_users.append(u_copy)

    filtered_requests = []
    for req in DOWNLOAD_REQUESTS:
        if req_filter == 'all' or req['status'].lower() == req_filter.lower():
            filtered_requests.append(req)

    return render_template(
        'admin_dashboard.html',
        market=market_info,
        market_trend=market_trend_data,
        users=formatted_users,
        download_requests=filtered_requests,
        feedbacks=USER_FEEDBACKS,
        equity_data=parse_fund_excel_from_db('equity_funds'),
        balancer_data=parse_fund_excel_from_db('balancer_funds'),
        debt_data=parse_fund_excel_from_db('debt_funds'),
        auto_approval_enabled=ADMIN_SETTINGS['auto_approval_enabled'],
        user_filter=user_filter,
        req_filter=req_filter,
        chat_messages=CHAT_MESSAGES
    )


@app.route('/admin/approve-download/<int:req_id>', methods=['POST'])
def approve_download(req_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    for req in DOWNLOAD_REQUESTS:
        if req['id'] == req_id:
            req['status'] = 'Approved'
            req['approved_at'] = datetime.now().isoformat()
            flash(f"Download request for {req['filename']} approved!", 'success')
            break
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reject-download/<int:req_id>', methods=['POST'])
def reject_download(req_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    for req in DOWNLOAD_REQUESTS:
        if req['id'] == req_id:
            req['status'] = 'Rejected'
            req['approved_at'] = None
            flash(f"Download request for {req['filename']} rejected.", 'danger')
            break
    return redirect(url_for('admin_dashboard'))


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
        except Exception as e:
            flash(f'Error updating category: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/upload-nav', methods=['GET', 'POST'])
def upload_nav():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        try:
            file = request.files.get('nav_image')
            if file and file.filename != '':
                raw_fn = file.filename
                filename = secure_filename(raw_fn) or 'latest_nav.jpg'
                file_bytes = file.read()
                
                with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'wb') as f:
                    f.write(file_bytes)
                with open(os.path.join(app.config['UPLOAD_FOLDER'], 'latest_nav.jpg'), 'wb') as f:
                    f.write(file_bytes)

                with open(os.path.join(app.config['UPLOAD_FOLDER'], 'nav_meta.json'), 'w') as mf:
                    json.dump({'filename': filename, 'original_filename': raw_fn}, mf)

                flash(f'Successfully published NAV: {filename}', 'success')
        except Exception as e:
            flash(f'Error uploading NAV image: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/upload-archive', methods=['GET', 'POST'])
def upload_archive():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        try:
            year = request.form.get('archive_year', datetime.now().strftime('%Y'))
            month_input = request.form.get('archive_month', 'Oct').strip().lower()
            month_map = {'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April', 'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August', 'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'}
            full_month_name = month_map.get(month_input[:3], 'October')
            saved_count = 0
            for file in request.files.getlist('archive_files'):
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    target_dir = os.path.join(ARCHIVE_FOLDER, year, full_month_name)
                    os.makedirs(target_dir, exist_ok=True)
                    file.save(os.path.join(target_dir, filename))
                    saved_count += 1
            flash(f'Successfully uploaded {saved_count} archive file(s)!', 'success')
        except Exception as e:
            flash(f'Error uploading archive files: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/get-archive-files', methods=['GET'])
def get_archive_files():
    year = request.args.get('year', '').strip()
    month_input = request.args.get('month', '').strip().lower()
    month_map = {'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April', 'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August', 'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'}
    full_month = month_map.get(month_input[:3], month_input.capitalize())
    target_dir = os.path.join(ARCHIVE_FOLDER, year, full_month)
    matched_files = []
    if os.path.exists(target_dir):
        try:
            for f in os.listdir(target_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                    matched_files.append(f)
        except Exception:
            pass
    return jsonify({'success': True, 'files': sorted(list(set(matched_files)), reverse=True)})


if __name__ == '__main__':
    app.run(debug=True)