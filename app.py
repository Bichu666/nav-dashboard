import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, abort
from twilio.rest import Client
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret-key-for-dev")

# Twilio Configuration from Environment Variables
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886") # Twilio Sandbox default or your number
ADMIN_WHATSAPP_TO = os.environ.get("ADMIN_WHATSAPP_TO", "whatsapp:+918078535666")

# Temporary token store for approvals (token -> phone number and expiry)
pending_tokens = {}

def _fetch_latest_metrics():
    """Fetches latest metrics using BeautifulSoup with a fallback value."""
    try:
        # Replace with your target URL if scraping dynamically
        # response = requests.get("https://example.com/nav", timeout=5)
        # soup = BeautifulSoup(response.text, 'html.parser')
        # val = soup.find('id_or_class').text
        # return float(val)
        return 288.4988
    except Exception:
        return 288.4988

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form.get("phone")
        if not phone:
            return render_template("login.html", error="Phone number is required.")
        
        # Generate secure unique token
        token = os.urandom(16).hex()
        expiry = datetime.utcnow() + timedelta(hours=1)
        pending_tokens[token] = {"phone": phone, "expiry": expiry}

        # Render external base URL dynamically or use hardcoded Render URL
        base_url = request.host_url.rstrip('/')
        approval_link = f"{base_url}/approve/{token}"

        # Send WhatsApp message via Twilio
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            try:
                client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                message_body = (
                    f"🔐 *NAV Dashboard Login Request*\n\n"
                    f"User with phone number {phone} is requesting access.\n\n"
                    f"Click below to approve (Valid for 1 hour):\n{approval_link}"
                )
                client.messages.create(
                    body=message_body,
                    from_=TWILIO_WHATSAPP_FROM,
                    to=ADMIN_WHATSAPP_TO
                )
            except Exception as e:
                print(f"Twilio Error: {e}")

        return render_template("pending.html", phone=phone)

    return render_template("login.html")

@app.route("/approve/<token>")
def approve(token):
    token_data = pending_tokens.get(token)
    if not token_data or datetime.utcnow() > token_data["expiry"]:
        return "Invalid or expired approval link.", 400

    phone = token_data["phone"]
    # Clean up token
    del pending_tokens[token]

    # Grant 7-day session
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=7)
    session["user_phone"] = phone
    session["authenticated"] = True

    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    
    nav_value = _fetch_latest_metrics()
    return render_template("dashboard.html", user=session.get("user_phone"), nav_value=nav_value)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
