import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Use /tmp directory for Render's read-only file system compatibility
DB_PATH = '/tmp/database.db'

# Initialize Database
def init_db():
    conn = sqlite3.connect(DB_PATH)
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

@app.route('/check_status', methods=['GET', 'POST'])
def check_status():
    if request.method == 'GET':
        return redirect(url_for('index'))
        
    phone = request.form.get('phone')
    
    if not phone:
        return redirect(url_for('index'))
        
    conn = sqlite3.connect(DB_PATH)
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
        return render_template('dashboard.html')
    else:
        return render_template('pending.html')

# --- Admin Routes ---

@app.route('/admin')
def admin():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, phone, status FROM users')
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

@app.route('/approve/<int:user_id>', methods=['POST'])
def approve(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'approved' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete/<int:user_id>', methods=['POST'])
def delete(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)