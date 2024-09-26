import secrets
import re
import main
from werkzeug.security import generate_password_hash, check_password_hash

#ststus: 0=inactive, 1=active

async def get_username_from_session(session_id):
    try:
        return main.session[session_id]
    except:
        return None
async def get_user_id_from_username(username):
    res = await main.db("SELECT id FROM users WHERE username = ?", (username,))
    return res[0][0]
async def get_user_email_from_username(username):
    res = await main.db("SELECT email FROM users WHERE username = ?", (username,))
    return res[0][0]
async def get_user_email_from_session(session_id):
    username = await get_username_from_session(session_id)
    res = await main.db("SELECT email FROM users WHERE username = ?", (username,))
    return res[0][0]
async def check_if_user_is_admin(username, type):
    if type == 'global':
        res = await main.db("SELECT 1 FROM user_groups WHERE id = ? AND admin LIKE ?", (main.GLOBAL_ADMIN, '%' + username + '%',))
        return len(res) > 0
    elif type == 'room':
        res = await main.db("SELECT 1 FROM user_groups WHERE id = ? AND admin LIKE ?", (main.ROOM_ADMIN, '%' + username + '%',))
        return len(res) > 0
    return False

async def signup(username, password, email):
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return "Invalid username format", 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Invalid email format", 400
    try:
        # Check if the username is already taken
        res = await main.db("SELECT * FROM users WHERE username = ?", (username,))
        if len(res) > 0:
            return "Username already taken", 400
        res = await main.db("SELECT * FROM unverified_users WHERE username = ?", (username,))
        if len(res) > 0:
            return "Check email", 400
        password_hash = generate_password_hash(password)
        await main.db("INSERT INTO unverified_users (username, password, email) VALUES (?, ?, ?)", (username, password_hash, email))
        await main.auth.send_confirmation_email(email)
        return "User registered successfully. Please check your email to verify your account", 201

    except Exception as e:
        print(f"An error occurred during signup: {e}")
        return "Internal Server Error", 500



async def login(username, password):
    try:
        # Check if the username exists in the database
        res = await main.db("SELECT * FROM users WHERE username = ?", (username,))
        if len(res) == 0:
            res = await main.db("SELECT * FROM unverified_users WHERE username = ?", (username,))
            if len(res) == 0:
                return "User not found", 404
            else:
                return "User not verified", 401
        else:
            # Check if the user is active
            if res[0][8] == 0:
                return "User is inactive", 401
            # Check if the password is correct
            if check_password_hash(res[0][2], password):
                session_id = secrets.token_hex(16)
                main.session[session_id] = username
                resp = main.make_response(main.jsonify("Login successful"))
                resp.set_cookie('session_id', session_id, max_age=3600, httponly=True, secure=True, samesite='Strict')
                return resp
            else:
                return "Incorrect password", 401
    except Exception as e:
        print(f"An error occurred during login: {e}")
        return "Internal Server Error", 500

async def logout(session_id):
    try:
        if session_id in main.session:
            del main.session[session_id]
            resp = main.make_response(main.jsonify("Logout successful"))
            resp.delete_cookie('session_id')
            return resp
        else:
            return "Session not found", 404
    except Exception as e:
        print(f"An error occurred during logout: {e}")
        return "Internal Server Error", 500


async def modify_user(session_id, target_username, action, password=None, bio=None, admin=False):
    try:
        # Verify session and get the username
        username = await get_username_from_session(session_id)
        if not username:
            return 'Unauthorized', 401
        if admin:
            user_groups = await main.groups.get_user_groups(session_id)
            user_groups = user_groups[0]
            # '[{"id": 1, "name": "admin"}]'
            group_ids = [group['id'] for group in user_groups]
            if not 1 in group_ids:
                return 'Forbidden', 403
        elif not username or username != target_username:
            return 'Unauthorized', 401

        # Perform the requested action
        if action == 'update':
            if password:
                password_hash = generate_password_hash(password)
                await main.db("UPDATE users SET password = ? WHERE username = ?", (password_hash, target_username))
            elif bio:
                await main.db("UPDATE users SET bio = ? WHERE username = ?", (bio, target_username))
            else:
                return "Missing param", 400
        elif action == 'delete':
            if admin:
                await main.db("DELETE FROM users WHERE username = ?", (target_username,))
            else:
                return 'Forbidden', 403
        elif action == 'deactivate':
            if admin:
                await main.db("UPDATE users SET status = 0 WHERE username = ?", (target_username,))
            else:
                return 'Forbidden', 403
        elif action == 'activate':
            if admin:
                await main.db("UPDATE users SET status = 1 WHERE username = ?", (target_username,))
            else:
                return 'Forbidden', 403

        return "User modified successfully", 200

    except Exception as e:
        print(f"An error occurred while modifying the user: {e}")
        return "Internal Server Error", 500


