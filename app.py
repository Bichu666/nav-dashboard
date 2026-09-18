from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'nav_portal_secret_key'

# Admin credentials
ADMIN_MOBILE = "+91807853566"
ADMIN_PASSWORD = "Bichu@5419"

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        
        # Check if login matches admin credentials
        if mobile == ADMIN_MOBILE and password == ADMIN_PASSWORD:
            session['user'] = mobile
            session['is_admin'] = True
            return redirect(url_for('dashboard'))
        else:
            # Regular user session
            session['user'] = mobile
            session['is_admin'] = False
            return redirect(url_for('dashboard'))
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Route to appropriate dashboard based on role
    if session.get('is_admin'):
        return render_template('dashboard.html')
    else:
        return render_template('user_dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
