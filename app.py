from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Route for your financial dashboard homepage
@app.route('/')
def home():
    return render_template('index.html')

# Route to reliably serve manifest.json from the static directory
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'manifest.json')

if __name__ == '__main__':
    app.run(debug=True)