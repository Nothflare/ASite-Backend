import aiohttp
import configparser
from itsdangerous import URLSafeTimedSerializer
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

async def check_user(session_id):
    if session_id is None or session_id not in main.session:
        return main.redirect(main.url_for('login'))
    return main.session[session_id]

