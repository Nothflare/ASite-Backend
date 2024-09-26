from functools import wraps
from flask import Flask, jsonify, request, make_response, session, url_for, sessions, redirect
from flask_cors import CORS
import asyncio
import json
from models import dash, posts, users, auth, groups, room_reservation
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
    try:
        data = json.loads(request.data)
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    if not username or not password or not email:
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        msg, code = await users.signup(username, password, email)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
async def login():
    try:
        data = json.loads(request.data)
        username = data.get('username')
        password = data.get('password')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    if not username or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        return await users.login(username, password)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/logout', methods=['GET'])
async def logout():
    session_id = request.cookies.get('session_id')
    try:
        return await users.logout(session_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/modify_user', methods=['POST'])
async def modify_user():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        target_username = data.get('target_username')
        action = data.get('action')
        password = data.get('password')
        bio = data.get('bio')
        admin = data.get('admin')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await users.modify_user(session_id, target_username, action, password, bio, admin)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_user_groups', methods=['GET'])
async def get_user_groups():
    try:
        session_id = request.cookies.get('session_id')
        username = request.args.get('username')
        if not username:
            username = await users.get_username_from_session(session_id)
        msg, code = await groups.get_user_groups(session_id, username)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create_group', methods=['POST'])
async def create_group():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        group_name = data.get('group_name')
        admin = data.get('admin')
        not_public = data.get('not_public')
        can_post_announcements = data.get('can_post_announcements')
        can_post_assessment = data.get('can_post_assessment')
        can_post_pull = data.get('can_post_pull')
        can_post_room_reservation = data.get('can_post_room_reservation')
        members = data.get('members')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await groups.create_group(session_id, group_name, admin, not_public, can_post_announcements, can_post_assessment, can_post_pull, can_post_room_reservation, members)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/modify_group', methods=['POST'])
async def modify_group():
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    session_id = request.cookies.get('session_id')
    group_name = data.get('group_name')
    action = data.get('action')
    admin = data.get('admin')
    not_public = data.get('not_public')
    can_post_announcements = data.get('can_post_announcements')
    can_post_assessment = data.get('can_post_assessment')
    can_post_pull = data.get('can_post_pull')
    can_post_room_reservation = data.get('can_post_room_reservation')
    members = data.get('members')
    try:
        msg, code = await groups.modify_group(session_id, group_name, action, admin, not_public, can_post_announcements, can_post_assessment, can_post_pull, can_post_room_reservation, members)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_public_groups_list', methods=['GET'])
async def get_public_groups():
    try:
        session_id = request.cookies.get('session_id')
        return await groups.get_public_group_list(session_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/join_public_group', methods=['POST'])
async def join_public_group():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        group_name = data.get('group_name')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await groups.join_public_group(session_id, group_name)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/leave_group', methods=['POST'])
async def leave_group():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        group_name = data.get('group_name')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await groups.leave_group(session_id, group_name)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/create_post', methods=['POST'])
async def create_post():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        title = data.get('title')
        content = data.get('content')
        post_type = data.get('post_type')
        permission = data.get('permission')
        post_as = data.get('post_as')
        start_at = data.get('start_at')
        end_at = data.get('end_at')
        label = data.get('label')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await posts.create_post(session_id, title, content, post_type, permission, post_as, start_at, end_at, label)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_posts', methods=['GET'])
async def get_posts():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        post_type = data.get('post_type')
        start_from = int(data.get('start_from'))
        view_type = data.get('view_type')
        id = data.get('id')
        admin = data.get('admin')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        return await posts.get_posts(session_id, post_type, start_from, view_type, id, admin)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_details', methods=['GET'])
async def get_details():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        post_id = data.get('post_id')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        return await posts.get_details(session_id, post_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_pull_details', methods=['GET'])
async def get_pull_details():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        post_id = data.get('post_id')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        return await posts.get_pull_details(session_id, post_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vote', methods=['POST'])
async def vote():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        post_id = data.get('post_id')
        vote = data.get('vote')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await posts.vote(session_id, post_id, vote)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/modify_post', methods=['POST'])
async def modify_post():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        post_id = data.get('post_id')
        action = data.get('action')
        title = data.get('title')
        content = data.get('content')
        label = data.get('label')
        permission = data.get('permission')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await posts.modify_post(session_id, post_id, action, title, content, label, permission)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/follow_post', methods=['POST'])
async def follow_post():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        post_id = data.get('post_id')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await posts.follow_post(session_id, post_id, "follow")
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/unfollow_post', methods=['POST'])
async def unfollow_post():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        post_id = data.get('post_id')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await posts.follow_post(session_id, post_id, "unfollow")
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_timeline', methods=['GET'])
async def get_timeline():
    try:
        session_id = request.cookies.get('session_id')
        return await posts.get_timeline(session_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create_room', methods=['POST'])
async def create_room():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        name = data.get('name')
        open_time = data.get('open_time')
        close_time = data.get('close_time')
        available_days = data.get('available_days')
        unavailable_periods = data.get('unavailable_periods')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await room_reservation.create_room(session_id, data, name, open_time, close_time, available_days, unavailable_periods)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/modify_room', methods=['POST'])
async def modify_room():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        room_id = data.get('room_id')
        action = data.get('action')
        name = data.get('name')
        open_time = data.get('open_time')
        close_time = data.get('close_time')
        available_days = data.get('available_days')
        unavailable_periods = data.get('unavailable_periods')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await room_reservation.modify_room(session_id, room_id, name, action, open_time, close_time, available_days, unavailable_periods)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/get_rooms', methods=['GET'])
async def get_rooms():
    try:
        session_id = request.cookies.get('session_id')
        data = json.loads(request.data)
        admin = data.get('admin')
        return await room_reservation.get_rooms(session_id, admin)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_available_rooms_by_time', methods=['GET'])
async def get_available_rooms_by_time():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        return await room_reservation.get_available_rooms_by_time(session_id, start_time, end_time)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_available_times_by_room', methods=['GET'])
async def get_available_times_by_room():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        room_id = data.get('room_id')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        return await room_reservation.get_available_times_by_room(session_id, room_id, start_time, end_time)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_reservations', methods=['GET'])
async def get_reservations():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        room_id = data.get('room_id')
        user =  data.get('user')
        admin = data.get('admin')
        return await room_reservation.get_reservations(session_id, room_id, start_time, end_time, user, admin)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reserve_room', methods=['POST'])
async def reserve_room():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        room_id = data.get('room_id')
        for_group = data.get('for_group')
        reason = data.get('reason')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await room_reservation.reserve_room(session_id, room_id, for_group, reason, start_time, end_time)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cancel_reservation', methods=['POST'])
async def cancel_reservation():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        reservation_id = data.get('reservation_id')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await room_reservation.cancel_reservation(session_id, reservation_id)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/approve_reservation', methods=['POST'])
async def approve_reservation():
    try:
        data = json.loads(request.data)
        session_id = request.cookies.get('session_id')
        reservation_id = data.get('reservation_id')
        action = data.get
        reason = data.get('reason')
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    try:
        msg, code = await room_reservation.approve_reservation(session_id, reservation_id, action, reason)
        return jsonify({'message': msg}), code
    except Exception as e:
        return jsonify({'error': str(e)}), 500



if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app.run()
    loop.run_until_complete(db(loop))