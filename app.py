from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Hardcoded Admin credentials as requested
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
            # Regular user login logic (or pending approval)
            session['user'] = mobile
            session['is_admin'] = False
            return redirect(url_for('dashboard'))
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Route to Admin Dashboard or User Dashboard based on session role
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
