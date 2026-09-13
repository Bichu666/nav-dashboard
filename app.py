from datetime import datetime, timedelta

# --- Inside your Admin Route (where you handle approvals) ---
if request.method == 'POST':
    action = request.form.get('action')
    mobile = request.form.get('mobile')
    
    if action == 'approve':
        # Set expiration to 30 days from today
        expiry_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        # Save both approval status and expiry date in your data storage/database
        approved_users[mobile] = expiry_date
        if mobile in pending_users:
            pending_users.remove(mobile)

# --- Inside your Login / Dashboard Route (where you check access) ---
@app.route('/dashboard')
def dashboard():
    mobile = session.get('user_mobile')
    if not mobile:
        return redirect(url_for('login'))
    
    # Check if user is approved and if approval is still valid (< 30 days)
    if mobile in approved_users:
        expiry_str = approved_users[mobile]
        expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
        
        if datetime.now() > expiry_date:
            # Approval has expired! Remove from approved and send to pending
            del approved_users[mobile]
            pending_users.append(mobile)
            return redirect(url_for('pending'))
    else:
        return redirect(url_for('pending'))
        
    # Proceed to render dashboard...
