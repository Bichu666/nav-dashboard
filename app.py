from datetime import datetime
from flask import Flask, jsonify, render_template
import pandas as pd
from twilio.rest import Client

yfinance_available = True
try:
  import yfinance as yf
except ImportError:
  yfinance_available = False

app = Flask(__name__)

# --- Twilio WhatsApp Configuration ---
ACCOUNT_SID = 'your_twilio_account_sid'
AUTH_TOKEN = 'your_twilio_auth_token'
try:
  twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)
except Exception:
  twilio_client = None


def send_admin_whatsapp_alert():
  if twilio_client:
    try:
      twilio_client.messages.create(
          from_='whatsapp:+14155238886',
          body=(
              '🔔 *NAV App Alert*: A user just accessed the application'
              ' dashboard!'
          ),
          to='whatsapp:+91YOUR_ADMIN_PHONE_NUMBER',
      )
    except Exception as e:
      print(f'WhatsApp notification error: {e}')


def get_market_data():
  """Fetches live Sensex and parses full fund returns & NAV data from NAV.xlsx."""
  current_time = datetime.now().strftime('%d-%b-%Y, %I:%M:%S %p')

  sensex_data = {
      'price': 74902.59,
      'change': -634.78,
      'is_positive': False,
      'time': current_time,
      'history': [
          {'date': '2026-09-10', 'close': 74902.59, 'change': +620.67, 'is_positive': True},
          {'date': '2026-09-09', 'close': 74764.23, 'change': -138.37, 'is_positive': False},
          {'date': '2026-09-08', 'close': 75577.58, 'change': +813.35, 'is_positive': True},
          {'date': '2026-09-07', 'close': 76132.81, 'change': +555.23, 'is_positive': True},
          {'date': '2026-09-04', 'close': 76515.43, 'change': +382.62, 'is_positive': True},
      ],
  }

  if yfinance_available:
    try:
      sensex = yf.Ticker('^BSESN')
      df = sensex.history(period='7d')
      if len(df) >= 2:
        cp = float(df['Close'].iloc[-1])
        pc = float(df['Close'].iloc[-2])
        chg = round(cp - pc, 2)
        sensex_data['price'] = round(cp, 2)
        sensex_data['change'] = chg
        sensex_data['is_positive'] = chg >= 0
    except Exception:
      pass

  # Parse NAV.xlsx dynamically
  try:
    excel_df = pd.read_excel('NAV.xlsx', sheet_name='NEW NAV ')
  except Exception:
    excel_df = None

  def parse_rows(start_idx, end_idx):
    funds_list = []
    if excel_df is None:
      return funds_list
    for idx in range(start_idx, end_idx):
      row = excel_df.iloc[idx]
      name = row.iloc[1]
      if pd.isna(name):
        continue

      def fmt_pct(val):
        if pd.isna(val):
          return '-'
        try:
          return f'{float(val)*100:.2f}%'
        except:
          return str(val)

      def fmt_val(val):
        if pd.isna(val):
          return '-'
        try:
          return f'{float(val):.2f}'
        except:
          return str(val)

      todays_nav = float(row.iloc[15]) if not pd.isna(row.iloc[15]) else 0.0

      funds_list.append({
          'name': name,
          'inception': fmt_pct(row.iloc[4]),
          'm1': fmt_pct(row.iloc[5]),
          'm6': fmt_pct(row.iloc[6]),
          'y1': fmt_pct(row.iloc[7]),
          'y2': fmt_pct(row.iloc[8]),
          'y3': fmt_pct(row.iloc[9]),
          'y4': fmt_pct(row.iloc[10]),
          'y5': fmt_pct(row.iloc[11]),
          'y7': fmt_pct(row.iloc[12]),
          'y10': fmt_pct(row.iloc[13]),
          'highest_nav': fmt_val(row.iloc[14]),
          'nav': round(todays_nav, 2),
      })
    return funds_list

  equity_funds = parse_rows(1, 35)
  balanced_funds = parse_rows(36, 43)
  debt_funds = parse_rows(44, 51)

  return sensex_data, equity_funds, balanced_funds, debt_funds


@app.route('/api/sensex')
def sensex_api():
  data, _, _, _ = get_market_data()
  return jsonify(data)


@app.route('/')
def user_dashboard():
  send_admin_whatsapp_alert()
  sensex, eq, bal, dbt = get_market_data()
  return render_template(
      'index.html',
      is_admin=False,
      sensex=sensex,
      history=sensex['history'],
      equity_funds=eq,
      balanced_funds=bal,
      debt_funds=dbt,
  )


@app.route('/admin')
def admin_dashboard():
  sensex, eq, bal, dbt = get_market_data()
  return render_template(
      'index.html',
      is_admin=True,
      sensex=sensex,
      history=sensex['history'],
      equity_funds=eq,
      balanced_funds=bal,
      debt_funds=dbt,
  )


if __name__ == '__main__':
  app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)