from flask import Flask, render_template, send_from_directory

app = Flask(__name__)

# --- PWA Static Asset Routes ---
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/json')

@app.route('/pwabuilder-sw.js')
def serve_service_worker():
    return send_from_directory('static', 'pwabuilder-sw.js', mimetype='application/javascript')

# --- Existing App Routes ---
@app.route('/')
def home():
    # Replace this with your actual home/dashboard route logic
    return render_template('index.html')

@app.route('/login')
def login():
    # Replace this with your actual login route logic
    return "Login Page"

if __name__ == '__main__':
    app.run(debug=True)