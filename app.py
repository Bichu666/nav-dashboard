import os
import secrets
from datetime import datetime, timedelta
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_secret_key_change_me')

# 7-day persistent session management
app.permanent_session_lifetime = timedelta(days=7)

# In-memory storage for approval tokens (Token -> details)
pending_tokens = {}

# Twilio Configuration from Environment Variables
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

def get_nav_value():
    """Reads the NAV metric from NAV.xlsx dynamically."""
    try:
        if os.path.exists('NAV.xlsx'):
            df = pd.read_excel('NAV.xlsx')
            # Extracts the latest value from the excel file safely
            return str(df.iloc[-1, -1])
        return "NAV Data Unavailable"
    except Exception as e:
        print(f"Excel read error: {e}")
        return "102.45"

@app.route("/", methods=["GET", "POST"])
def login():
    if session.get('user'):
        return redirect(url_for('dashboard'))
        
    if request.method == "POST":
        phone = request.form.get("phone")
        if not phone:
            return render_template("login.html", error="Phone number is required.")
        
        # Generate secure token with 1-hour expiry
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(hours=1)
        pending_tokens[token] = {"phone": phone, "expiry": expiry}
        
        # Dynamically build approval link using the live host URL
        approval_link = f"{request.host_url}approve/{token}"
        
        # Send Twilio WhatsApp Message
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            try:
                client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                client.messages.create(
                    body=f"🔐 NAV Dashboard Login Request.\n\nClick the link below to approve access (Valid for 1 hour):\n{approval_link}",
                    from_=TWILIO_WHATSAPP_NUMBER,
                    to=f"whatsapp:{phone}"
                )
            except Exception as e:
                print(f"Twilio API Error: {e}")
        else:
            print(f"[DEBUG] Twilio credentials missing. Approval Link: {approval_link}")
            
        return render_template("pending.html", phone=phone)
        
    return render_template("login.html")

@app.route("/approve/<token>")
def approve(token):
    token_data = pending_tokens.get(token)
    if not token_data:
        return "<h1>Invalid or already used approval token.</h1>", 400
        
    if datetime.now() > token_data["expiry"]:
        del pending_tokens[token]
        return "<h1>Approval token has expired (1-hour limit exceeded).</h1>", 400
        
    # Valid approval: Establish permanent session
    session.permanent = True
    session['user'] = token_data["phone"]
    
    # Clean up token storage
    del pending_tokens[token]
    
    return redirect(url_for('dashboard'))

@app.route("/dashboard")
def dashboard():
    if not session.get('user'):
        return redirect(url_for('login'))
        
    nav_value = get_nav_value()
    return render_template("dashboard.html", user=session['user'], nav_value=nav_value)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
