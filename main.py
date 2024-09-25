import re
from functools import wraps
from flask import Flask, jsonify, request, make_response, session, url_for, sessions, redirect
from flask_cors import CORS
import json
import asyncio
from models import dash, posts, users, auth, groups
import secrets
import aiosmtplib
import aiosqlite
import configparser

app = Flask(__name__)
CORS(app)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

loop = asyncio.get_event_loop()

config = configparser.ConfigParser()
config.read('config.conf')

DATABASE_PATH = config['database']['path']
SECRET_KEY = config['app']['secret_key']
BACKEND_VERSION = config['app']['version']
SMTP_PASSWORD = config['email']['smtp_password']
SMTP_SERVER = config['email']['smtp_server']
SMTP_PORT = config['email']['smtp_port']
EMAIL_USERNAME = config['email']['smtp_username']
SMTP_USE_TLS = config['email']['smtp_use_tls']
GLOBAL_ADMIN = config['user_groups']['global_admin']
ROOM_ADMIN = config['user_groups']['room_admin']

app.secret_key = SECRET_KEY

async def db(exp, params=None):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as conn:
            async with conn.cursor() as cur:
                if params:
                    await cur.execute(exp, params)
                else:
                    await cur.execute(exp)
                if exp.strip().upper().startswith("SELECT"):
                    r = await cur.fetchall()
                    return r
                else:
                    await conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")

async def send_email(email, subject, message):
    try:
        async with aiosmtplib.SMTP(hostname=SMTP_SERVER, port=SMTP_PORT) as smtp:
            await smtp.connect()
            await smtp.starttls()
            await smtp.login(EMAIL_USERNAME, SMTP_PASSWORD)
            message = f"Subject: {subject}\n\n{message}"
            await smtp.sendmail(EMAIL_USERNAME, email, message)
            await smtp.quit()
    except aiosmtplib.SMTPException as e:
        raise

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.cookies.get('session_id')
        if session_id is None or session_id not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
async def index():
    return BACKEND_VERSION, 200

@app.route('/confirm/<token>')
async def confirm_email(token):
    try:
        msg, code = await auth.confirm_email(token)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/signup', methods=['POST'])
async def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    if not username or not password or not email:
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        msg, code = await users.signup(username, password, email)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
async def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        msg, code = await users.login(username, password)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/logout', methods=['GET'])
async def logout():
    session_id = request.cookies.get('session_id')
    try:
        msg, code = await users.logout(session_id)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/modify_user', methods=['POST'])
@login_required
async def modify_user():
    data = request.json
    session_id = request.cookies.get('session_id')
    target_username = data.get('target_username')
    action = data.get('action')
    password = data.get('password')
    bio = data.get('bio')
    admin = data.get('admin')
    try:
        msg, code = await users.modify_user(session_id, target_username, action, password, bio, admin)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500







if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app.run()
    loop.run_until_complete(db(loop))