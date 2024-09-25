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

@app.route("/signup", methods=['POST'])
async def signup():
    if request.method == 'POST':
        try:
            # in json format
            data = json.loads(request.data)
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            if not username or not password or not email:
                return "Missing username, password or email", 400
            return await users.signup(username, password, email)
        except Exception as e:
            print(f"An error occurred during signup: {e}")
            return "Internal Server Error", 500
    return "Invalid request method", 405

@app.route('/confirm/<token>')
async def confirm_email(token):
    try:
        response, status_code = await auth.confirm_email(token)
        return response, status_code
    except Exception as e:
        print(f"An error occurred while confirming email: {e}")
        return "Internal Server Error", 500

@app.route("/login", methods=['POST'])
async def login():
    try:
        # in json format
        data = json.loads(request.data)
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return "Missing username or password", 400
        return await users.login(username, password)
    except Exception as e:
        print(f"An error occurred during login: {e}")
        return "Internal Server Error", 500

@app.route("/modify_user", methods=['POST'])
async def modify_user():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return "Unauthorized", 401

        data = json.loads(request.data)
        target_user = data.get('target_user')
        action = data.get('action')
        password = data.get('password')
        bio = data.get('bio')

        if not target_user or not action:
            return "Missing target_user or action", 400

        response, status_code = await users.modify_user(session_id, target_user, action, password, bio)
        return response, status_code
    except Exception as e:
        print(f"An error occurred while modifying the user: {e}")
        return "Internal Server Error", 500

@app.route("/get_post_details/<int:post_id>", methods=['GET'])
async def get_post_list(post_id):
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return "Unauthorized", 401

        response, status_code = await posts.get_details(session_id, post_id)
        return response, status_code
    except Exception as e:
        print(f"An error occurred while fetching post list: {e}")
        return "Internal Server Error", 500

@app.route("/get_list/<post_type>", methods=['GET'])
async def get_post_list(post_type):
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return "Unauthorized", 401

        start_from = request.args.get('start_from', 0)
        response, status_code = await posts.get_posts(session_id, post_type, int(start_from))
        return response, status_code
    except Exception as e:
        print(f"An error occurred while fetching post list: {e}")
        return "Internal Server Error", 500
@app.route("/vote", methods=['POST'])
async def vote():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return "Unauthorized", 401
        data = json.loads(request.data)
        post_id = data.get('post_id')
        opinion = data.get('opinion')
        if not post_id or not opinion:
            return "Missing post_id or opinion", 400
        return await posts.vote(session_id, post_id, opinion)
    except Exception as e:
        print(f"An error occurred while submitting vote: {e}")
        return "Internal Server Error", 500

@app.route("/modify_post", methods=['POST'])
async def modify_post():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return "Unauthorized", 401
        data = json.loads(request.data)
        post_id = data.get('post_id')
        action = data.get('action')
        title = data.get('title')
        content = data.get('content')
        label = data.get('label')
        permission = data.get('permission')
        if not post_id or not action:
            return "Missing post_id or action", 400
        return await posts.modify_post(session_id, post_id, action, title, content, label, permission)
    except Exception as e:
        print(f"An error occurred while modifying the post: {e}")
        return "Internal Server Error", 500







if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app.run()
    loop.run_until_complete(db(loop))