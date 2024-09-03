import secrets
import re
from main import db, session, make_response
from auth import send_confirmation_email
from werkzeug.security import generate_password_hash, check_password_hash

async def signup(username, password, email, scode):
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return "Invalid username format", 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Invalid email format", 400
    # Check if the username is already taken
    res = await db(r"SELECT * FROM users WHERE username = '{}'".format(username))
    if len(res) > 0:
        return "Username already taken", 400
    else:
        res = await db(r"SELECT * FROM inactive_users WHERE username = '{}'".format(username))
        if len(res) > 0:
            return "Check email", 400
        password_hash = generate_password_hash(password)
    try:
        await db(r"INSERT INTO inactive_users (username, password, email) VALUES ('{}', '{}', '{}')".format(username, password_hash, email))
        await send_confirmation_email(email)
        return "User registered successfully. Please check your email to verify your account", 201
    except:
        return "Error", 500



async def login(username, password):
    # Check if the username exists in the database
    res = await db(r"SELECT * FROM users WHERE username = '{}'".format(username))
    if len(res) == 0:
        res = await db(r"SELECT * FROM inactive_users WHERE username = '{}'".format(username))
        if len(res) == 0:
            return "User not found", 404
        else:
            return "User not verified", 401
    else:
        # Check if the password is correct
        if check_password_hash(res[0][2], password):
            session_id = secrets.token_hex(16)
            session[session_id] = username
            resp = make_response("Login successful")
            resp.set_cookie('session_id', session_id, max_age=3600, httponly=True, secure=True, samesite='Strict')
            return resp
        else:
            return "Incorrect password", 401
async def logout(username):
    return 0
async def get_user(username, id):
    res = await db(r"SELECT user FROM users WHERE id = {}".format(id))
    return res
async def get_user_details(user, id):
    return "1"