import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory

app = Flask(__name__)
app.secret_key = "nav_dashboard_secure_key"

APPROVED_USERS = ["+919876543210"]  # Default Admin
PENDING_USERS = []
VISITOR_LOGS = []
FEEDBACK_LIST = []
EXCEL_FILE = "NAV.xlsx"

# Storage for Old NAV files (month-wise from 2024 onwards) and Today's NAV
OLD_NAV_FILES = {}
TODAY_NAV_FILE = {"name": "No file uploaded yet", "path": ""}

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_categorized_nav_data():
    categorized_data = {"Equity Funds": [], "Balanced Funds": [], "Debt Funds": []}
    if not os.path.exists(EXCEL_FILE):
        return categorized_data
    
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='NEW NAV ')
        current_category = "Equity Funds"
        
        for i in range(len(df)):
            row = df.iloc[i]
            col0 = str(row.iloc[0]).strip().upper()
            
            if "EQUITY" in col0 or "E Q U I T Y" in col0:
                current_category = "Equity Funds"
                continue
            elif "BALANCED" in col0:
                current_category = "Balanced Funds"
                continue
            elif "DEBT" in col0:
                current_category = "Debt Funds"
                continue
                
            fund_name = row.iloc[1]
            if pd.isna(fund_name):
                continue
                
            fund_obj = {
                "fund_name": str(fund_name).strip(),
                "latest_nav": row.iloc[15]
            }
            if current_category in categorized_data:
                categorized_data[current_category].append(fund_obj)
    except Exception as e:
        print("Excel processing error:", e)
        
    return categorized_data

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
    
    nav_data = load_categorized_nav_data()
    sensex = {"current": "81,450.20", "change": "-125.40", "status": "down"}
    
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
        old_nav_files=OLD_NAV_FILES,
        today_nav_file=TODAY_NAV_FILE,
        admin_name="Bijoosh Padmakumar"
    )

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    global TODAY_NAV_FILE
    if request.method == "POST":
        action = request.form.get("action")
        mobile = request.form.get("mobile")
        
        if action == "approve" and mobile in PENDING_USERS:
            PENDING_USERS.remove(mobile)
            if mobile not in APPROVED_USERS:
                APPROVED_USERS.append(mobile)
        elif action == "deny" and mobile in PENDING_USERS:
            PENDING_USERS.remove(mobile)
            
        # Handle Master Excel Update
        if "excel_file" in request.files:
            file = request.files["excel_file"]
            if file.filename != '':
                file.save(EXCEL_FILE)

        # Handle Today's NAV Image/File Upload
        if "today_nav_file" in request.files:
            t_file = request.files["today_nav_file"]
            if t_file.filename != '':
                filepath = os.path.join(UPLOAD_FOLDER, t_file.filename)
                t_file.save(filepath)
                TODAY_NAV_FILE = {"name": t_file.filename, "path": t_file.filename}

        # Handle Old Month-wise NAV Image/File Upload (2024 to present)
        if "old_nav_month" in request.form and "old_nav_file" in request.files:
            month_year = request.form.get("old_nav_month")
            o_file = request.files["old_nav_file"]
            if month_year and o_file.filename != '':
                filepath = os.path.join(UPLOAD_FOLDER, o_file.filename)
                o_file.save(filepath)
                OLD_NAV_FILES[month_year] = o_file.filename

    return render_template(
        "admin.html", 
        pending_users=PENDING_USERS, 
        approved_users=APPROVED_USERS, 
        visitor_logs=VISITOR_LOGS,
        feedback_list=FEEDBACK_LIST,
        old_nav_files=OLD_NAV_FILES,
        today_nav_file=TODAY_NAV_FILE,
        admin_name="Bijoosh Padmakumar"
    )

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

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
