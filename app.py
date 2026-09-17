import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Initialize Database
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

# Run database setup when the app starts
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check_status', methods=['POST'])
def check_status():
    phone = request.form.get('phone')
    
    if not phone:
        return redirect(url_for('index'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if the mobile number already exists in the database
    cursor.execute('SELECT status FROM users WHERE phone = ?', (phone,))
    user = cursor.fetchone()
    
    if user is None:
        # If it's a new number, insert it with 'pending' status
        cursor.execute('INSERT INTO users (phone, status) VALUES (?, ?)', (phone, 'pending'))
        conn.commit()
        status = 'pending'
    else:
        status = user[0]  # Gets 'pending' or 'approved'
        
    conn.close()
    
    # Direct user based on approval status
    if status == 'approved':
        return "Welcome to your Dashboard!"
    else:
        return render_template('pending.html')

if __name__ == '__main__':
    app.run(debug=True)