from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    # Renders your main login page (index.html)
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        # Safely extract form data or JSON payload
        data = request.form if request.form else (request.json or {})
        
        # Extract phone or mobile number safely
        phone_number = data.get('phone', data.get('mobile', data.get('sense', '')))
        
        # Clean the phone string if it exists
        if phone_number:
            clean_phone = str(phone_number).replace('+', '').strip()
        else:
            clean_phone = "User"
        
        print(f"Processing login for: {clean_phone}")
        
        # Pass BOTH phone and sense to dashboard.html to prevent UndefinedError
        return render_template('dashboard.html', phone=clean_phone, sense=clean_phone)
        
    except Exception as e:
        # Catch and report any runtime errors clearly
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)