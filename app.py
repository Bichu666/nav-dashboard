from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Route for your financial dashboard homepage
@app.route('/')
def home():
    # Replace this with your actual dashboard rendering code or template
    return render_template('index.html')

# Route to serve manifest.json for PWA / Android Trusted Web Activity
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('.', 'manifest.json')

if __name__ == '__main__':
    app.run(debug=True)