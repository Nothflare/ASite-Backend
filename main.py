import re
from functools import wraps
from flask import Flask, jsonify, request, make_response, session, url_for, sessions, redirect
from flask_cors import CORS
import json
import asyncio
from models import dash, posts, users, auth
import secrets
import aiosqlite
import configparser


'''
database format:
- users
    - id
    - username
    - password
    - email
    - created_at
    - updated_at
    - bio
    - profile_pic
    - login_status
- inactive_users
    - username
    - password
    - email
    - created_at
- posts
    - id
    - title
    - content
    - author
    - created_at
    - updated_at
- votes
    - id
    - post_id
    - user_id
    - vote
'''
app = Flask(__name__)
CORS(app)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

loop = asyncio.get_event_loop()

config = configparser.ConfigParser()
config.read('config.conf')

DATABASE_PATH = config['database']['path']
SECRET_KEY = config['app']['secret_key']
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
    return await dash.pong()

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
    return await auth.confirm_email(token)

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

@app.route("/get_user")
async def get_user():
    user_id = request.args.get('id')
    return await users.get_user(1,user_id)

@app.route("/get_posts")
async def get_posts():
    return await posts.get_posts(1)






if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app.run()
    loop.run_until_complete(db(loop))