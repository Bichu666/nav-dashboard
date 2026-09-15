from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    # Renders your main login or dashboard interface
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        # Get phone number from form data or JSON request
        data = request.form if request.form else request.json
        phone_number = data.get('phone', '') if data else ''
        
        # Safely sanitize phone input to remove symbols like '+'
        clean_phone = phone_number.replace('+', '').strip()
        
        # Log the activity
        print(f"Processing login for phone: {clean_phone}")
        
        # Render the dashboard template upon successful login instead of raw JSON
        return render_template('dashboard.html', phone=clean_phone)
        
    except Exception as e:
        # Catch any runtime error and return a clean message
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)