from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Temporary storage for demo (or linked to your data logic)
pending_users = []
approved_users = {}  # Stores mobile: expiry_date_string

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        session['user_mobile'] = mobile
        if mobile in approved_users:
            expiry_date = datetime.strptime(approved_users[mobile], '%Y-%m-%d %H:%M:%S')
            if datetime.now() > expiry_date:
                del approved_users[mobile]
                pending_users.append(mobile)
                return redirect(url_for('pending'))
            return redirect(url_for('dashboard'))
        else:
            if mobile not in pending_users:
                pending_users.append(mobile)
            return redirect(url_for('pending'))
    return render_template('login.html')

@app.route('/pending')
def pending():
    return render_template('pending.html')

@app.route('/dashboard')
def dashboard():
    mobile = session.get('user_mobile')
    if not mobile:
        return redirect(url_for('login'))
    
    if mobile in approved_users:
        expiry_date = datetime.strptime(approved_users[mobile], '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expiry_date:
            del approved_users[mobile]
            pending_users.append(mobile)
            return redirect(url_for('pending'))
    else:
        return redirect(url_for('pending'))
        
    return render_template('dashboard.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        action = request.form.get('action')
        mobile = request.form.get('mobile')
        if action == 'approve':
            expiry_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            approved_users[mobile] = expiry_date
            if mobile in pending_users:
                pending_users.remove(mobile)
    return render_template('admin.html', pending_users=pending_users, admin_name="Bijoosh Padmakumar")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
