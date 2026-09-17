from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def home():
    # Renders the login page where users enter their phone number
    return render_template('index.html')

@app.route('/check_status', methods=['POST', 'GET'])
def check_status():
    if request.method == 'POST':
        phone = request.form.get('phone')
        # Add your backend logic here (e.g., database lookup, OTP generation, etc.)
        
        # For now, return a success response or render a confirmation page
        return f"Approval requested successfully for mobile number: {phone}"
        
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)