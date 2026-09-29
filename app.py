import yfinance as yf
from flask import Flask, render_template

app = Flask(__name__)


def get_sensex_data():
  try:
    # Fetch BSE Sensex data (^BSESN) from Yahoo Finance
    sensex = yf.Ticker('^BSESN')
    hist = sensex.history(period='7d')  # Get last 7 days to ensure 5 trading days

    if hist.empty:
      raise ValueError('No data fetched')

    latest_row = hist.iloc[-1]
    prev_row = hist.iloc[-2]

    current_val = latest_row['Close']
    prev_close = prev_row['Close']
    points_change = current_val - prev_close
    pct_change = (points_change / prev_close) * 100

    formatted_current = f'{current_val:,.2f}'
    formatted_points = (
        f'+{points_change:,.2f}' if points_change >= 0 else f'{points_change:,.2f}'
    )
    formatted_pct = (
        f'+{pct_change:.2f}' if pct_change >= 0 else f'{pct_change:.2f}'
    )

    # Prepare previous 5 days trend list
    trend_data = []
    last_5 = hist.tail(5)

    for i in range(len(last_5)):
      row = last_5.iloc[i]
      date_str = row.name.strftime('%b %d')
      val = f"{row['Close']:,.2f}"

      if i > 0:
        p_val = last_5.iloc[i - 1]['Close']
        chg = ((row['Close'] - p_val) / p_val) * 100
        chg_str = f'+{chg:.2f}' if chg >= 0 else f'{chg:.2f}'
      else:
        chg_str = '0.00'

      trend_data.append({
          'date': date_str,
          'value': val,
          'change': chg_str,
          'points_change': chg_str,
      })

    sensex_live = {
        'value': formatted_current,
        'change_pts': formatted_points,
        'change_pct': formatted_pct,
        'is_positive': points_change >= 0,
    }

    return sensex_live, trend_data

  except Exception as e:
    # Fallback default data if network fails
    fallback_live = {
        'value': '72,771.72',
        'change_pts': '-1,124.02',
        'change_pct': '-1.52%',
        'is_positive': False,
    }
    fallback_trend = [
        {'date': 'Sep 21', 'value': '73,100.00', 'change': '-0.45', 'points_change': '-0.45'},
        {'date': 'Sep 22', 'value': '73,500.00', 'change': '+0.55', 'points_change': '+0.55'},
        {'date': 'Sep 23', 'value': '73,200.00', 'change': '-0.41', 'points_change': '-0.41'},
        {'date': 'Sep 24', 'value': '73,890.00', 'change': '+0.94', 'points_change': '+0.94'},
        {'date': 'Sep 25', 'value': '72,771.72', 'change': '-1.52', 'points_change': '-1.52'},
    ]
    return fallback_live, fallback_trend


@app.route('/user-dashboard')
def user_dashboard():
  sensex_live, sensex_trend = get_sensex_data()
  return render_template(
      'user_dashboard.html',
      sensex_live=sensex_live,
      sensex_trend=sensex_trend,
  )


@app.route('/admin-dashboard')
def admin_dashboard():
  sensex_live, sensex_trend = get_sensex_data()
  return render_template(
      'admin_dashboard.html',
      sensex_live=sensex_live,
      sensex_trend=sensex_trend,
  )


if __name__ == '__main__':
  app.run(debug=True)