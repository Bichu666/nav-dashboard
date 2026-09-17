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
        # Render the pending template and pass the phone number to it
        return render_template('pending.html', phone=phone)
        
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)