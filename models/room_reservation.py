import main
import datetime

async def create_room(session_id, name, open_time, close_time, available_days, unavailable_periods):
    try:
        username = await main.users.get_username_from_session(session_id)
        is_admin = await main.users.check_if_user_is_admin(username, 'global')
        if not is_admin:
            is_admin = await main.users.check_if_user_is_admin(username, 'room')
        if not is_admin:
            return 'Unauthorized', 401

        await main.db(
            "INSERT INTO rooms (name, open_time, close_time, available_days, unavailable_periods) VALUES (?, ?, ?, ?, ?)",
            (name, open_time, close_time, ','.join(map(str, available_days)), ','.join(map(str, unavailable_periods)))
        )
        return 'Room created', 200
    except Exception as e:
        print(f"An error occurred while creating room: {e}")
        return 'Internal Server Error', 500

async def modify_room(session_id, room_id, name=None, open_time=None, close_time=None, available_days=None, unavailable_periods=None, status=None):
    try:
        username = await main.users.get_username_from_session(session_id)
        is_admin = await main.users.check_if_user_is_admin(username, 'global')
        if not is_admin:
            is_admin = await main.users.check_if_user_is_admin(username, 'room')
        if not is_admin:
            return 'Unauthorized', 401

        query = "UPDATE rooms SET "
        params = []
        if name:
            query += "name = ?, "
            params.append(name)
        if open_time:
            query += "open_time = ?, "
            params.append(open_time)
        if close_time:
            query += "close_time = ?, "
            params.append(close_time)
        if available_days:
            query += "available_days = ?, "
            params.append(','.join(map(str, available_days)))
        if unavailable_periods:
            query += "unavailable_periods = ?, "
            params.append(','.join(map(str, unavailable_periods)))
        if status:
            query += "status = ?, "
            params.append(status)

        query = query.rstrip(', ')
        query += " WHERE id = ?"
        params.append(room_id)

        await main.db(query, params)
        return 'Room modified', 200
    except Exception as e:
        print(f"An error occurred while modifying room: {e}")
        return 'Internal Server Error', 500

async def delete_room(session_id, room_id):
    try:
        username = await main.users.get_username_from_session(session_id)
        is_admin = await main.users.check_if_user_is_admin(username, 'global')
        if not is_admin:
            is_admin = await main.users.check_if_user_is_admin(username, 'room')
        if not is_admin:
            return 'Unauthorized', 401
        await main.db("DELETE FROM rooms WHERE id = %s", (room_id,))
        return 'Room deleted', 200
    except Exception as e:
        print(f"An error occurred while deleting room: {e}")
        return 'Internal Server Error', 500

async def get_rooms(session_id, admin = False):
    try:
        if admin:
            username = await main.users.get_username_from_session(session_id)
            is_admin = await main.users.check_if_user_is_admin(username, 'global')
            if not is_admin:
                is_admin = await main.users.check_if_user_is_admin(username, 'room')
            if not is_admin:
                return 'Unauthorized', 401
            rooms = await main.db("SELECT * FROM rooms")

        else:
            username = await main.users.get_username_from_session(session_id)
            if not username:
                return 'Unauthorized', 401
            rooms = await main.db("SELECT id, name FROM rooms WHERE status = 1")
        rooms = main.json.dumps(rooms)
        return rooms, 200
    except Exception as e:
        print(f"An error occurred while fetching rooms: {e}")
        return 'Internal Server Error', 500

import datetime

async def get_available_rooms_by_time(session_id, start_time, end_time):
    try:
        username = await main.users.get_username_from_session(session_id)
        if not username:
            return 'Unauthorized', 401

        # Get the day of the week for the start_time (1=Sunday, 7=Saturday)
        start_day = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S').isoweekday() % 7 + 1
        end_day = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S').isoweekday() % 7 + 1

        # Query to get active and open rooms available on the specified days
        query = """
        SELECT r.id, r.name, r.unavailable_periods
        FROM rooms r
        LEFT JOIN reservations res ON r.id = res.room_id
        WHERE r.status = 1
        AND ? IN (r.available_days)
        AND ? IN (r.available_days)
        AND (res.start_time IS NULL OR res.end_time IS NULL OR
             (res.start_time NOT BETWEEN ? AND ?) AND
             (res.end_time NOT BETWEEN ? AND ?))
        """
        rooms = await main.db(query, (start_day, end_day, start_time, end_time, start_time, end_time))

        available_rooms = []
        for room in rooms:
            room_id, room_name, unavailable_periods_str = room
            unavailable_periods = unavailable_periods_str.split(',') if unavailable_periods_str else []
            is_available = True
            for period in unavailable_periods:
                period_start, period_end = period.split('-')
                if (start_time < period_end and end_time > period_start):
                    is_available = False
                    break
            if is_available:
                available_rooms.append((room_id, room_name))

        available_rooms = main.json.dumps(available_rooms)
        return available_rooms, 200
    except Exception as e:
        print(f"An error occurred while fetching available rooms: {e}")
        return 'Internal Server Error', 500

async def get_available_times_by_room(session_id, room_id, start_time, end_time):
    try:
        username = await main.users.get_username_from_session(session_id)
        if not username:
            return 'Unauthorized', 401

        # Intervals should not longer than 3 hours
        if (datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')).seconds > 10800:
            return 'Intervals should not longer than 3 hours', 400

        # Get room details
        room_query = "SELECT open_time, close_time, available_days, unavailable_periods FROM rooms WHERE id = ? AND status = 1"
        room = await main.db(room_query, (room_id,))
        if not room:
            return 'Room not found or inactive', 404

        open_time, close_time, available_days, unavailable_periods_str = room[0]
        available_days = list(map(int, available_days.split(',')))
        unavailable_periods = unavailable_periods_str.split(',') if unavailable_periods_str else []

        # Get the day of the week for the start_time (1=Sunday, 7=Saturday)
        start_day = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S').isoweekday() % 7 + 1
        end_day = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S').isoweekday() % 7 + 1

        if start_day not in available_days or end_day not in available_days:
            return 'Room not available on the specified days', 400

        # Get reservations for the room within the specified time period
        reservations_query = """
        SELECT start_time, end_time
        FROM reservations
        WHERE room_id = ?
        AND approval_status IN (1, 2)  -- Approved or pending reservations
        AND ((start_time BETWEEN ? AND ?) OR (end_time BETWEEN ? AND ?))
        """
        reservations = await main.db(reservations_query, (room_id, start_time, end_time, start_time, end_time))

        # Calculate available times
        available_times = []
        current_time = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')

        while current_time < datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S'):
            next_time = min(datetime.datetime.strptime(close_time, '%Y-%m-%d %H:%M:%S'), datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S'))
            for reservation in reservations:
                res_start = datetime.datetime.strptime(reservation[0], '%Y-%m-%d %H:%M:%S')
                res_end = datetime.datetime.strptime(reservation[1], '%Y-%m-%d %H:%M:%S')
                if res_start <= current_time < res_end:
                    next_time = min(next_time, res_start)
                    break
            for period in unavailable_periods:
                period_start, period_end = period.split('-')
                period_start = datetime.datetime.strptime(period_start, '%Y-%m-%d %H:%M:%S')
                period_end = datetime.datetime.strptime(period_end, '%Y-%m-%d %H:%M:%S')
                if period_start <= current_time < period_end:
                    next_time = min(next_time, period_start)
                    break
            if current_time < next_time:
                available_times.append((current_time.strftime('%Y-%m-%d %H:%M:%S'), next_time.strftime('%Y-%m-%d %H:%M:%S')))
            current_time = next_time

        return main.json.dumps(available_times), 200
    except Exception as e:
        print(f"An error occurred while fetching available times: {e}")
        return 'Internal Server Error', 500

async def get_reservations(session_id, start_time, end_time, room=None, user=None, admin = False):
    try:
        username = await main.users.get_username_from_session(session_id)
        if not username:
            return 'Unauthorized', 401
        if admin:
            is_admin = await main.users.check_if_user_is_admin(username, 'global')
            if not is_admin:
                is_admin = await main.users.check_if_user_is_admin(username, 'room')
            if not is_admin:
                return 'Unauthorized', 401

            query = """
            SELECT id, room_id, username, for, reason, start_time, end_time, created_at, approval_status, approved_by, approved_at, approved_reason
            FROM reservations
            WHERE (start_time BETWEEN ? AND ? OR end_time BETWEEN ? AND ?)
            """
            params = [start_time, end_time, start_time, end_time]
            if room:
                query += " AND room_id = ?"
                params.append(room)
            if user:
                query += " AND username = ?"
                params.append(user)

            reservations = await main.db(query, params)
        else:
            query = """
            SELECT id, room_id, username, for, reason, start_time, end_time, created_at, approval_status
            FROM reservations
            WHERE (start_time BETWEEN ? AND ? OR end_time BETWEEN ? AND ?)
            """
            params = [start_time, end_time, start_time, end_time]
            if room:
                query += " AND room_id = ?"
                params.append(room)
            if user:
                query += " AND username = ?"
                params.append(user)

            reservations = await main.db(query, params)
        reservations = main.json.dumps(reservations)
        return reservations, 200
    except Exception as e:
        print(f"An error occurred while fetching reservations: {e}")
        return 'Internal Server Error', 500

async def reserve_room(session_id, room_id, for_group, reason, start_time, end_time):
    try:
        username = await main.users.get_username_from_session(session_id)
        if not username:
            return 'Unauthorized', 401
        if not (await main.groups.get_post_permissions(session_id, for_group, 'room_reservation')):
            return 'Unauthorized', 401

        # Check if the interval is longer than 3 hours
        if (datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')).seconds > 10800:
            return 'Intervals should not be longer than 3 hours', 400

        # Check if the room is available between start_time and end_time
        availability_query = """
        SELECT COUNT(*)
        FROM reservations
        WHERE room_id = ?
        AND approval_status IN (1, 2)  -- Approved or pending reservations
        AND ((start_time BETWEEN ? AND ?) OR (end_time BETWEEN ? AND ?))
        """
        count = await main.db(availability_query, (room_id, start_time, end_time, start_time, end_time))
        if count[0][0] > 0:
            return 'Room is not available during the specified time', 400

        # Get room details
        room_query = "SELECT open_time, close_time, available_days, unavailable_periods FROM rooms WHERE id = ? AND status = 1"
        room = await main.db(room_query, (room_id,))
        if not room:
            return 'Room not found or inactive', 404

        open_time, close_time, available_days, unavailable_periods_str = room[0]
        available_days = list(map(int, available_days.split(',')))
        unavailable_periods = unavailable_periods_str.split(',') if unavailable_periods_str else []
        start_day = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S').isoweekday() % 7 + 1
        end_day = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S').isoweekday() % 7 + 1

        if start_day not in available_days or end_day not in available_days:
            return 'Room not available on the specified days', 400
        for period in unavailable_periods:
            period_start, period_end = period.split('-')
            if start_time < period_end and end_time > period_start:
                return 'Room is not available during the specified time', 400

        # Insert the reservation into the database and get the reservation_id
        insert_query = """
        INSERT INTO reservations (room_id, username, for, reason, start_time, end_time, approval_status)
        VALUES (?, ?, ?, ?, ?, ?, 0)  -- 0 means pending approval
        """
        reservation_id = await main.db(insert_query, (room_id, username, for_group, reason, start_time, end_time), return_last_id=True)

        # Send email to user
        user_email = await main.users.get_user_email_from_session(session_id)
        email_subject = "Room Reservation Created"
        email_body = f"Your reservation (ID: {reservation_id}) for room {room_id} from {start_time} to {end_time} is pending approval."
        await main.send_email(user_email, email_subject, email_body)

        return 'Reservation created and pending approval', 200
    except Exception as e:
        print(f"An error occurred while reserving the room: {e}")
        return 'Internal Server Error', 500

async def cancel_reservation(session_id, reservation_id):
    try:
        username = await main.users.get_username_from_session(session_id)
        if not username:
            return 'Unauthorized', 401

        # Check if the reservation exists and is made by the user
        reservation = await main.db("SELECT username FROM reservations WHERE id = ?", (reservation_id,))
        if not reservation:
            return 'Reservation not found', 404
        elif reservation[0][0] != username:
            return 'Unauthorized', 401
        # Delete the reservation
        await main.db("DELETE FROM reservations WHERE id = ?", (reservation_id,))
        return 'Reservation canceled', 200
    except Exception as e:
        print(f"An error occurred while canceling the reservation: {e}")
        return 'Internal Server Error', 500


async def approve_reservation(session_id, reservation_id, action, reason):
    try:
        username = await main.users.get_username_from_session(session_id)
        is_admin = await main.users.check_if_user_is_admin(username, 'global')
        if not is_admin:
            is_admin = await main.users.check_if_user_is_admin(username, 'room')
        if not is_admin:
            return 'Unauthorized', 401

        if action == 'approve':
            approval_status = 1
            email_subject = "Room Reservation Approved"
        elif action == 'reject':
            approval_status = 2
            email_subject = "Room Reservation Rejected"
        else:
            return 'Invalid action', 400

        # Retrieve reservation details
        reservation = await main.db(
            "SELECT name, start_time, end_time FROM reservations WHERE id = ?",
            (reservation_id,))
        if not reservation:
            return 'Reservation not found', 404

        # Update the reservation
        await main.db(
            "UPDATE reservations SET approval_status = ?, approved_by = ?, approved_at = NOW(), approved_reason = ? WHERE id = ?",
            (approval_status, username, reason, reservation_id))

        room_name, start_time, end_time = reservation[0]

        # Send email to user
        user_email = await main.users.get_user_email_from_session(session_id)
        if action == 'approve':
            email_body = f"Your reservation (ID: {reservation_id}) for room {room_name} from {start_time} to {end_time} has been approved."
        else:
            email_body = f"Your reservation (ID: {reservation_id}) for room {room_name} from {start_time} to {end_time} has been rejected. Reason: {reason}"

        await main.send_email(user_email, email_subject, email_body)

        return f'Reservation {action}ed', 200
    except Exception as e:
        print(f"An error occurred while approving the reservation: {e}")
        return 'Internal Server Error', 500