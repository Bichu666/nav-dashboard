from datetime import datetime, timedelta, timezone
import json
import os
import re
import shutil
import smtplib
import threading
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pandas as pd
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'nav_updates_secret_key'

app.permanent_session_lifetime = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=['10000 per day', '1000 per hour'],
    storage_uri='memory://',
)

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL) if DATABASE_URL else None

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ARCHIVE_FOLDER = 'archive_nav'
os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

ADMIN_ACTIVITY = {'last_active': datetime.now()}
ADMIN_SETTINGS = {'auto_approval_enabled': True}
ADMIN_EMAIL = 'bijooshpadmakumar522@gmail.com'
ADMIN_MOBILE = '+918078535666'

REGISTERED_USERS = [
    {
        'id': 1,
        'name': 'Rahul Sharma',
        'mobile': '+91 9876543210',
        'status': 'Pending',
        'registered_at': datetime.now() - timedelta(minutes=3),
        'approved_at': None,
    },
    {
        'id': 2,
        'name': 'Priya Nair',
        'mobile': '+91 9876522888',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(days=5),
        'approved_at': datetime.now().isoformat(),
    },
    {
        'id': 3,
        'name': 'biju',
        'mobile': '+917034788666',
        'status': 'Approved',
        'registered_at': datetime.now() - timedelta(days=10),
        'approved_at': datetime.now().isoformat(),
    },
]

USER_FEEDBACKS = [
    {
        'id': 1,
        'username': 'Rahul Sharma',
        'feedback': 'Great portal! Very intuitive and fast NAV updates.',
        'rating': 5,
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    },
    {
        'id': 2,
        'username': 'Priya Nair',
        'feedback': (
            'The historical archive search feature is extremely useful.'
        ),
        'rating': 5,
        'timestamp': datetime.now().strftime('%b %d, %Y, %I:%M %p'),
    },
]

DOWNLOAD_REQUESTS = []


def check_user_validity(user):
  if not ADMIN_SETTINGS.get('auto_approval_enabled', True):
    return
  now = datetime.now()
  if user['status'] == 'Pending':
    reg_time = user.get('registered_at', now)
    if now - reg_time > timedelta(minutes=5):
      user['status'] = 'Approved'
      user['approved_at'] = now.isoformat()

  if user['status'] == 'Approved' and user.get('approved_at'):
    approved_date = datetime.fromisoformat(user['approved_at'])
    if now - approved_date > timedelta(days=30):
      user['status'] = 'Pending'
      user['approved_at'] = None
      user['registered_at'] = now


def get_festival_greeting():
  now_utc = datetime.now(timezone.utc)
  ist_now = now_utc + timedelta(hours=5, minutes=30)
  m = ist_now.month
  d = ist_now.day
  y = ist_now.year

  festivals_by_date = {
      (2026, 1, 1): 'Happy New Year',
      (2026, 1, 14): 'Happy Makar Sankranti / Pongal',
      (2026, 1, 26): 'Happy Republic Day',
      (2026, 2, 15): 'Happy Maha Shivaratri',
      (2026, 3, 4): 'Happy Holi',
      (2026, 3, 19): 'Happy Ugadi / Gudi Padwa',
      (2026, 3, 26): 'Happy Rama Navami',
      (2026, 3, 31): 'Happy Mahavir Jayanti',
      (2026, 4, 3): 'Happy Good Friday',
      (2026, 4, 14): 'Happy Vishu
