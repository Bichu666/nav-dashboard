import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nav-dashboard-secret-key')

# Explicit routes to serve PWA files directly from root URL for PWABuilder
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/pwabuilder-sw.js')
def serve_sw():
    return send_from_directory('static', 'pwabuilder-sw.js')

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        # Add your admin approval / login logic here
        return redirect(url_for('index'))
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)