import secrets
import re
import main
from werkzeug.security import generate_password_hash, check_password_hash

#ststus: 0=inactive, 1=active

async def get_username_from_session(session_id):
    return main.session[session_id]

async def get_user_email_from_session(session_id):
    username = await get_username_from_session(session_id)
    res = await main.db("SELECT email FROM users WHERE username = ?", (username,))
    return res[0][0]

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
                resp = main.make_response("Login successful")
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
            resp = main.make_response("Logout successful")
            resp.delete_cookie('session_id')
            return resp, 200
        else:
            return "Session not found", 404
    except Exception as e:
        print(f"An error occurred during logout: {e}")
        return "Internal Server Error", 500


async def modify_user(session_id, target_user_email, action, password=None, bio=None):
    try:
        current_user = await get_username_from_session(session_id)
        is_admin = await main.db("SELECT * FROM user_groups WHERE id = (SELECT `group` FROM users WHERE username = %s) AND name = 'admin'", (current_user,))

        if password:
            password_hash = generate_password_hash(password)
            await main.db("UPDATE users SET password = %s WHERE email = %s", (password_hash, target_user_email))

        if bio:
            await main.db("UPDATE users SET bio = %s WHERE email = %s", (bio, target_user_email))

        if action == 'delete' and is_admin:
            await main.db("DELETE FROM users WHERE email = %s", (target_user_email,))

        if action == 'deactivate' and is_admin:
            await main.db("UPDATE users SET login_status = 0 WHERE email = %s", (target_user_email,))

        return "User modified successfully", 200

    except Exception as e:
        return "Internal Server Error", 500

async def forget_password(email):
    try:
        res = await main.db("SELECT * FROM users WHERE email = ?", (email,))
        if len(res) == 0:
            return "User not found", 404
        else:
            token = await main.auth.generate_confirmation_token(email)
            reset_url = main.url_for('reset_password', token=token, _external=True)
            html = f'Please click the link to reset your password: <a href="{reset_url}">{reset_url}</a>'
            subject = "Password Reset"
            await main.send_email(email, subject, html)
            return "Password reset email sent", 200

    except Exception as e:
        print(f"An error occurred during password reset: {e}")
        return "Internal Server Error", 500

async def reset_password(token, password):
    try:
        email = await main.auth.confirm_token(token)
        if not email:
            return 'The reset link is invalid or has expired.', 400
        password_hash = generate_password_hash(password)
        await main.db("UPDATE users SET password = %s WHERE email = %s", (password_hash, email))
        return 'Password reset successfully', 200
    except Exception as e:
        print(f"An error occurred during password reset: {e}")
        return "Internal Server Error", 500