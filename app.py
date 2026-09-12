import os
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here')

# In-memory storage for pending requests and active user sessions
pending_requests = []
approved_users = set()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_phone = request.form.get('phone')
        if not user_phone:
            return "Phone number is required", 400
            
        formatted_phone = user_phone.strip()
        if not formatted_phone.startswith('+'):
            formatted_phone = '+' + formatted_phone
            
        if formatted_phone not in pending_requests and formatted_phone not in approved_users:
            pending_requests.append(formatted_phone)
            
        return render_template('pending.html', phone=formatted_phone)
        
    return render_template('login.html')

@app.route('/admin')
def admin_panel():
    return render_template('admin.html', requests=pending_requests)

@app.route('/admin/approve/<path:phone>')
def admin_approve(phone):
    if phone in pending_requests:
        pending_requests.remove(phone)
    approved_users.add(phone)
    return redirect(url_for('admin_panel'))

@app.route('/check-status')
def check_status():
    phone = request.args.get('phone')
    if phone in approved_users:
        session['authenticated_user'] = phone
        return redirect(url_for('dashboard'))
    return render_template('pending.html', phone=phone, waiting=True)

@app.route('/dashboard')
def dashboard():
    if 'authenticated_user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['authenticated_user'])

@app.route('/logout')
def logout():
    user = session.pop('authenticated_user', None)
    if user in approved_users:
        approved_users.remove(user)
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
