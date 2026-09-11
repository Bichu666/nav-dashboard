import os
from datetime import datetime, timedelta
from flask import Flask, redirect, render_template, request, session, url_for
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-nav-key")

# Twilio Configuration from Environment Variables
account_sid = os.environ.get(
    "TWILIO_ACCOUNT_SID", "AC25437381c6c0d1f97dc83aff9480d580"
)
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.environ.get(
    "TWILIO_PHONE_NUMBER", "whatsapp:+14155238886"
)

# Admin WhatsApp number configured to your personal number
ADMIN_WHATSAPP = "whatsapp:+918078535666"

# In-memory session tracking for tokens and 7-day access windows
# Structure: { phone_number: expiry_datetime }
active_sessions = {}
# Structure: { token: { "phone": phone_number, "expires": datetime } }
pending_tokens = {}


@app.route("/", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    phone = request.form.get("phone").strip()
    formatted_phone = phone if phone.startswith("+") else f"+91{phone}"

    # Check if user already has an active 7-day access window
    if formatted_phone in active_sessions:
      if datetime.now() < active_sessions[formatted_phone]:
        session["user"] = formatted_phone
        return redirect(url_for("dashboard"))

    # Generate a secure random token for approval
    import secrets

    token = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta(hours=1)
    pending_tokens[token] = {"phone": formatted_phone, "expires": expiry}

    # Build approval and rejection URLs pointing back to the live app
    # (Render will automatically handle the host domain)
    base_url = request.host_url.rstrip("/")
    approve_link = f"{base_url}/approve/{token}"
    reject_link = f"{base_url}/reject/{token}"

    # Send WhatsApp notification to Admin
    if auth_token:
      try:
        client = Client(account_sid, auth_token)
        message_body = (
            f"🔐 *NAV Dashboard Access Request*\n\n"
            f"User Phone: {formatted_phone}\n\n"
            f"Click below to approve (Valid for 1 hour):\n{approve_link}\n\n"
            f"Click below to reject:\n{reject_link}"
        )
        client.messages.create(
            from_=twilio_phone_number,
            body=message_body,
            to=ADMIN_WHATSAPP,
        )
      except Exception as e:
        print(f"Twilio Error: {e}")

    return render_template("pending.html", phone=formatted_phone)

  return render_template("login.html")


@app.route("/approve/<token>")
def approve(token):
  if token not in pending_tokens:
    return "Invalid or already used approval link.", 400

  token_data = pending_tokens[token]
  if datetime.now() > token_data["expires"]:
    del pending_tokens[token]
    return "This approval link has expired (1-hour limit reached).", 400

  phone = token_data["phone"]
  # Grant 7 days of recurring access
  active_sessions[phone] = datetime.now() + timedelta(days=7)

  # Clean up token
  del pending_tokens[token]

  return (
      "<h3>Access Approved Successfully!</h3><p>The user has been granted 7"
      " days of access to the NAV Dashboard.</p>"
  )


@app.route("/reject/<token>")
def reject(token):
  if token in pending_tokens:
    del pending_tokens[token]
    return "<h3>Access Request Rejected.</h3>"
  return "Invalid or already processed link.", 400


@app.route("/dashboard")
def dashboard():
  user = session.get("user")
  if not user or user not in active_sessions:
    return redirect(url_for("login"))
  if datetime.now() > active_sessions[user]:
    session.pop("user", None)
    return redirect(url_for("login"))

  return render_template("dashboard.html", user=user)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
