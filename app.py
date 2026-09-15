from flask import Flask, render_template, request, jsonify, redirect, url_for

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
        
        # Check for multiple possible field names ('phone', 'mobile', or 'sense')
        phone_number = data.get('phone', data.get('mobile', data.get('sense', '')))
        
        # Clean the phone string if it exists, otherwise use a placeholder
        if phone_number:
            clean_phone = str(phone_number).replace('+', '').strip()
        else:
            clean_phone = "User"
        
        print(f"Processing login for: {clean_phone}")
        
        # Pass both phone and sense to dashboard.html
        return render_template('dashboard.html', phone=clean_phone, sense=clean_phone)
        
    except Exception as e:
        # Catch and report any runtime errors clearly
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/logout')
def logout():
    # Redirect user back to the home/login page
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)