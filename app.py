from flask import Flask, render_template, jsonify, send_from_directory

app = Flask(__name__)

# --- PWA Manifest Route (Direct JSON) ---
@app.route('/manifest.json')
def serve_manifest():
    return jsonify({
        "name": "NAV Financial Dashboard",
        "short_name": "NAV App",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#000000",
        "icons": [
            {
                "src": "/static/icon.png",
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    })

# --- Service Worker Route ---
@app.route('/pwabuilder-sw.js')
def serve_service_worker():
    return send_from_directory('static', 'pwabuilder-sw.js', mimetype='application/javascript')

# --- Existing App Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    return "Login Page"

if __name__ == '__main__':
    app.run(debug=True)