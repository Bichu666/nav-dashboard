import os
import json
from flask import Flask, render_template, request, redirect, url_for, session
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here')

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_phone = request.form.get('phone')
        if not user_phone:
            return "Phone number is required", 400
            
        formatted_phone = user_phone.strip()
        if not formatted_phone.startswith('+'):
            formatted_phone = '+' + formatted_phone
            
        approval_link = url_for('approve', phone=formatted_phone, _external=True)
        
        try:
            # Using Twilio's default sandbox template SID and variables to bypass ContentSid error
            message = twilio_client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                to=f"whatsapp:{formatted_phone}",
                content_sid="HXb5b62575e6e4ff6129ad7c8efe1f983e",
                content_variables=json.dumps({
                    "1": "NAV Dashboard Login", 
                    "2": approval_link
                })
            )
            print(f"Twilio template message sent successfully: {message.sid}")
        except Exception as e:
            print(f"Twilio API Error: {e}")
            
        return render_template('pending.html', phone=formatted_phone)
        
    return render_template('login.html')

@app.route('/approve')
def approve():
    phone = request.args.get('phone')
    if phone:
        session['authenticated_user'] = phone
        return redirect(url_for('dashboard'))
    return "Invalid approval request", 400

@app.route('/dashboard')
def dashboard():
    if 'authenticated_user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['authenticated_user'])

@app.route('/logout')
def logout():
    session.pop('authenticated_user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
