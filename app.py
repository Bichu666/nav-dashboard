from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')  # Or return your dashboard HTML/response

@app.route('/login', methods=['POST'])
def login():
    try:
        # Get phone number from form data or JSON request
        data = request.form if request.form else request.json
        phone_number = data.get('phone', '')

        # Safely sanitize phone input to remove symbols like '+'
        clean_phone = phone_number.replace('+', '').strip()

        # Your authentication or database logic here
        print(f"Processing login for phone: {clean_phone}")

        return jsonify({"status": "success", "message": "Logged in successfully"})
    except Exception as e:
        # Catch any runtime error and return a clean message instead of a 500 crash
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)