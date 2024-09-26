import configparser
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash
import main

config = configparser.ConfigParser()
config.read('config.conf')

# EMAIL = config['email']['email']

SECRET_KEY = config['app']['secret_key']
SECURITY_PASSWORD_SALT =  config['app']['security_password_salt']

async def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(email, salt=SECURITY_PASSWORD_SALT)

async def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    try:
        email = serializer.loads(
            token,
            salt=SECURITY_PASSWORD_SALT,
            max_age=expiration
        )
    except:
        return False
    return email

async def send_confirmation_email(email):
    token = await generate_confirmation_token(email)
    confirm_url = main.url_for('confirm_email', token=token, _external=True)
    html = f'Please click the link to confirm your email: <a href="{confirm_url}">{confirm_url}</a>'
    subject = "Please confirm your email"
    return await main.send_email(email, subject, html)

async def confirm_email(token):
    email = await confirm_token(token)
    if not email:
        return 'The confirmation link is invalid or has expired.', 400

    try:
        info = await main.db("SELECT * FROM unverified_users WHERE email = %s", (email,))
        if not info:
            return 'User not found', 404

        await main.db("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (info[0][0], info[0][1], info[0][2]))
        await main.db("DELETE FROM unverified_users WHERE email = %s", (email,))
    except Exception as e:
        return 'Internal Server Error', 500

    return 'You have confirmed your account. You can now login.', 200

async def forget_password(email):
    try:
        res = await main.db("SELECT * FROM users WHERE email = ?", (email,))
        if len(res) == 0:
            return "User not found", 404
        else:
            token = await generate_confirmation_token(email)
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
        email = await confirm_token(token)
        if not email:
            return 'The reset link is invalid or has expired.', 400
        password_hash = generate_password_hash(password)
        await main.db("UPDATE users SET password = %s WHERE email = %s", (password_hash, email))
        return 'Password reset successfully', 200
    except Exception as e:
        print(f"An error occurred during password reset: {e}")
        return "Internal Server Error", 500
