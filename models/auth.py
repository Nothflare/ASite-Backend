import aiohttp
import aiosmtplib
import configparser
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from main import url_for, db, session, redirect

config = configparser.ConfigParser()
config.read('config.conf')

EMAIL = config['email']['email']
PASSWORD = config['email']['password']
SMTP_SERVER = config['email']['smtp_server']
SMTP_PORT = config['email']['smtp_port']
EMAIL_USERNAME = config['email']['email_username']
SECRET_KEY = config['app']['secret_key']
SECURITY_PASSWORD_SALT =  config['app']['security_password_salt']

async def send_email(email, subject, message):
    async with aiosmtplib.SMTP(hostname=SMTP_SERVER, port=SMTP_PORT) as smtp:
        await smtp.connect()
        await smtp.starttls()
        await smtp.login(EMAIL_USERNAME, PASSWORD)
        message = f"Subject: {subject}\n\n{message}"
        await smtp.sendmail(EMAIL, email, message)
        await smtp.quit()

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
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = f'Please click the link to confirm your email: <a href="{confirm_url}">{confirm_url}</a>'
    subject = "Please confirm your email"
    return await send_email(email, subject, html)

async def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        return 'The confirmation link is invalid or has expired.', 400
    info = await db(r"SELECT * FROM inactive_users WHERE email = '{}'".format(email))
    if len(info) == 0:
        return 'User not found', 404
    else:
        await db(r"INSERT INTO users (username, password, email) VALUES ('{}', '{}', '{}')".format(info[0][0], info[0][1], info[0][2]))
        await db(r"DELETE FROM inactive_users WHERE email = '{}'".format(email))
    return 'You have confirmed your account. You can now login.', 200

async def check_user(session_id):
    if session_id is None or session_id not in session:
        return redirect(url_for('login'))
    return session[session_id]