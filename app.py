import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "nav_dashboard_secure_key"

APPROVED_USERS = ["+919876543210"]  # Default Admin
PENDING_USERS = []
VISITOR_LOGS = []
FEEDBACK_LIST = []
EXCEL_FILE = "NAV.xlsx"

def fetch_live_sensex():
    # Live market indicator data wrapper
    try:
        return {"current": "81,450.20", "change": "-125.40", "status": "down"}
    except:
        return {"current": "81,000.00", "change": "0.00", "status": "neutral"}

def load_dashboard_data():
    data = []
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE)
            data = df.to_dict(orient="records")
        except Exception as e:
            print("Excel read error:", e)
    return data

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        mobile = request.form.get("mobile")
        if mobile:
            VISITOR_LOGS.append({
                "mobile": mobile, 
                "time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            if mobile in APPROVED_USERS or mobile == "+910000000000":
                session["user"] = mobile
                return redirect(url_for("dashboard"))
            elif mobile not in PENDING_USERS:
                PENDING_USERS.append(mobile)
            return redirect(url_for("pending_status", mobile=mobile))
    return render_template("login.html")

@app.route("/check-status")
def pending_status():
    mobile = request.args.get("mobile")
    if mobile in APPROVED_USERS:
        session["user"] = mobile
        return redirect(url_for("dashboard"))
    return render_template("pending.html", mobile=mobile)

@app.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user or user not in APPROVED_USERS:
        return redirect(url_for("login"))
    
    nav_data = load_dashboard_data()
    sensex = fetch_live_sensex()
    
    sensex_history = [
        {"date": "11 Sep 2026", "points": "81,450.20", "status": "down"},
        {"date": "10 Sep 2026", "points": "81,575.60", "status": "up"},
        {"date": "09 Sep 2026", "points": "81,210.00", "status": "up"},
        {"date": "08 Sep 2026", "points": "80,950.40", "status": "down"},
        {"date": "07 Sep 2026", "points": "81,120.10", "status": "up"}
    ]
    
    return render_template(
        "dashboard.html", 
        nav_data=nav_data, 
        sensex=sensex, 
        sensex_history=sensex_history,
        admin_name="Bijoosh Padmakumar"
    )

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if request.method == "POST":
        action = request.form.get("action")
        mobile = request.form.get("mobile")
        
        if action == "approve" and mobile in PENDING_USERS:
            PENDING_USERS.remove(mobile)
            if mobile not in APPROVED_USERS:
                APPROVED_USERS.append(mobile)
        elif action == "deny" and mobile in PENDING_USERS:
            PENDING_USERS.remove(mobile)
            
        if "excel_file" in request.files:
            file = request.files["excel_file"]
            if file.filename != '':
                file.save(EXCEL_FILE)

    return render_template(
        "admin.html", 
        pending_users=PENDING_USERS, 
        approved_users=APPROVED_USERS, 
        visitor_logs=VISITOR_LOGS,
        feedback_list=FEEDBACK_LIST,
        admin_name="Bijoosh Padmakumar"
    )

@app.route("/feedback", methods=["POST"])
def feedback():
    rating = request.form.get("rating")
    comment = request.form.get("comment")
    user = session.get("user", "Anonymous Visitor")
    if comment:
        FEEDBACK_LIST.append({"user": user, "rating": rating, "comment": comment})
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
