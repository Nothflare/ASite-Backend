from idlelib.mainmenu import menudefs

import main

# group_admin, can_post_announcement is a list of usernames

async def get_user_groups(session_id, username = None):
    # only admin can specify username
    try:
        current_user = await main.users.get_username_from_session(session_id)
        if not username:
            username = current_user
        # Check if the user is in the member list of the group with id = 1
        else:
            is_admin = await main.users.check_if_user_is_admin(username, 'global')
            if not is_admin:
                return "Unauthorized", 401
        # return group id and group name in json format
        groups = await main.db("SELECT id, name FROM user_groups WHERE member LIKE ?", ('%' + username + '%',))
        # Convert the result to JSON format
        res = []
        for group in groups:
            res.append({
                'id': group[0],
                'name': group[1]
            })
        return res,200
    except Exception as e:
        print(f"An error occurred while fetching the user's groups: {e}")
        return "Internal Server Error", 500

async def create_group(session_id, group_name, admin, not_public = 0, can_post_announcement=None, can_post_assessment=None, can_post_pull=None, can_post_room_reservation=None, members=None):
    try:
        if not group_name:
            return "Group name is required", 400
        else:
            group_name = group_name.encode('utf-8')
            if len(group_name) > 50:
                return "Group name is too long", 400
        if not admin:
            return "Admin is required", 400
        if not not_public:
            not_public = 0
        if not can_post_announcement:
            can_post_announcement = []
        if not can_post_assessment:
            can_post_assessment = []
        if not can_post_pull:
            can_post_pull = []
        if not can_post_room_reservation:
            can_post_room_reservation = []
        if not members:
            members = []
        for permission in [can_post_announcement, can_post_assessment, can_post_pull, can_post_room_reservation, members]:
            if not isinstance(permission, list):
                return "Invalid permission list", 400
        current_user = await main.users.get_username_from_session(session_id)
        is_admin = await main.users.check_if_user_is_admin(current_user, 'global')
        if not is_admin:
            return "Unauthorized", 401
        # Check if admin is in the member list
        if admin not in members:
            members.append(admin)

        # Insert the new group into the database
        await main.db('''
            INSERT INTO user_groups (name, admin, not_public, can_post_announcement, can_post_assessment, can_post_pull, can_post_room_reservation, member)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (group_name, admin, not_public, ','.join(can_post_announcement), ','.join(can_post_assessment), ','.join(can_post_pull), ','.join(can_post_room_reservation), ','.join(members)))

        return "Group created successfully", 201
    except Exception as e:
        print(f"An error occurred while creating the group: {e}")
        return "Internal Server Error", 500

async def modify_group(session_id, group_id, action, subject):
    try:
        if not group_id:
            return "Group id is required", 400
        if not action:
            return "Action is required", 400
        current_user = await main.users.get_username_from_session(session_id)
        # Check if the user is in the member list of the group with id = 1 or is admin in the current group
        is_admin = await main.users.check_if_user_is_admin(current_user, 'global')
        if not is_admin:
            is_admin = await main.db("SELECT 1 FROM user_groups WHERE id = ? AND admin LIKE ?", (group_id, '%' + current_user + '%',))
            if not is_admin:
                return "Unauthorized", 401
        if action == 'delete':
            # Delete the group from the database
            await main.db("DELETE FROM user_groups WHERE id = ?", (group_id,))
            return "Group deleted successfully", 200
        elif action == 'visibility':
            # Reverse the visibility of the group
            current_visibility = await main.db("SELECT not_public FROM user_groups WHERE id = ?", (group_id,))
            current_visibility = current_visibility[0][0]
            await main.db("UPDATE user_groups SET not_public = ? WHERE id = ?", (1 - current_visibility, group_id))
            return "Visibility changed successfully", 200
        elif action == 'change_name':
            if not subject or not isinstance(subject, str):
                return "Invalid group name", 400
            # encode the group name
            subject = subject.encode('utf-8')
            if len(subject) > 50:
                return "Group name is too long", 400
            await main.db("UPDATE user_groups SET name = ? WHERE id = ?", (subject, group_id))
            return "Group name changed successfully", 200
        elif action == 'add_admin':
            if not subject or not isinstance(subject, list):
                return "Invalid admin", 400
            current_admin = await main.db("SELECT admin FROM user_groups WHERE id = ?", (group_id,))
            current_admin = current_admin[0][0].split(',')
            for admin in subject:
                if admin not in current_admin:
                    current_admin.append(admin)
            await main.db("UPDATE user_groups SET admin = ? WHERE id = ?", (','.join(current_admin), group_id))
            return "Admin added successfully", 200
        elif action == 'remove_admin':
            if not subject or not isinstance(subject, list):
                return "Invalid admin", 400
            current_admin = await main.db("SELECT admin FROM user_groups WHERE id = ?", (group_id,))
            current_admin = current_admin[0][0].split(',')
            for admin in subject:
                if admin in current_admin:
                    current_admin.remove(admin)
            await main.db("UPDATE user_groups SET admin = ? WHERE id = ?", (','.join(current_admin), group_id))
            return "Admin removed successfully", 200
        elif action == 'add_member':
            if not subject or not isinstance(subject, list):
                return "Invalid member", 400
            current_members = await main.db("SELECT member FROM user_groups WHERE id = ?", (group_id,))
            current_members = current_members[0][0].split(',')
            for member in subject:
                if member not in current_members:
                    current_members.append(member)
            await main.db("UPDATE user_groups SET member = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member added successfully", 200
        elif action == 'remove_member':
            if not subject or not isinstance(subject, list):
                return "Invalid member", 400
            current_members = await main.db("SELECT member FROM user_groups WHERE id = ?", (group_id,))
            current_members = current_members[0][0].split(',')
            for member in subject:
                if member in current_members:
                    current_members.remove(member)
            await main.db("UPDATE user_groups SET member = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member removed successfully", 200
        elif action == 'add_can_post_announcement':
            if not subject or not isinstance(subject, list):
                return "Invalid user", 400
            current_members = await main.db("SELECT can_post_announcement FROM user_groups WHERE id = ?", (group_id,))
            current_members = current_members[0][0].split(',')
            for member in subject:
                if member not in current_members:
                    current_members.append(member)
            await main.db("UPDATE user_groups SET can_post_announcement = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member added successfully", 200
        elif action == 'remove_can_post_announcement':
            if not subject or not isinstance(subject, list):
                return "Invalid user", 400
            current_members = await main.db("SELECT can_post_announcement FROM user_groups WHERE id = ?", (group_id,))
            current_members = current_members[0][0].split(',')
            for member in subject:
                if member in current_members:
                    current_members.remove(member)
            await main.db("UPDATE user_groups SET can_post_announcement = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member removed successfully", 200
        elif action == 'add_can_post_assessment':
            if not subject or not isinstance(subject, list):
                return "Invalid user", 400
            current_members = await main.db("SELECT can_post_assessment FROM user_groups WHERE id = ?", (group_id,))
            current_members = current_members[0][0].split(',')
            for member in subject:
                if member not in current_members:
                    current_members.append(member)
            await main.db("UPDATE user_groups SET can_post_assessment = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member added successfully", 200
        elif action == 'remove_can_post_assessment':
            if not subject or not isinstance(subject, list):
                return "Invalid user", 400
            current_members = await main.db("SELECT can_post_assessment FROM user_groups WHERE id = ?", (group_id,))
            current_members = current_members[0][0].split(',')
            for member in subject:
                if member in current_members:
                    current_members.remove(member)
            await main.db("UPDATE user_groups SET can_post_assessment = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member removed successfully", 200
        elif action == 'add_can_post_pull':
            if not subject or not isinstance(subject, list):
                return "Invalid user", 400
            current_members = await main.db("SELECT can_post_pull FROM user_groups WHERE id = ?", (group_id,))
            current_members = current_members[0][0].split(',')
            for member in subject:
                if member not in current_members:
                    current_members.append(member)
            await main.db("UPDATE user_groups SET can_post_pull = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member added successfully", 200
        elif action == 'remove_can_post_pull':
            if not subject or not isinstance(subject, list):
                return "Invalid user", 400
            current_members = await main.db("SELECT can_post_pull FROM user_groups WHERE id = ?", (group_id,))
            current_members = current_members[0][0].split(',')
            for member in subject:
                if member in current_members:
                    current_members.remove(member)
            await main.db("UPDATE user_groups SET can_post_pull = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member removed successfully", 200
        elif action == 'add_can_post_room_reservation':
            if not subject or not isinstance(subject, list):
                return "Invalid user", 400
            current_members = await main.db("SELECT can_post_room_reservation FROM user_groups WHERE id = ?", (group_id,))
            current_members = current_members[0][0].split(',')
            for member in subject:
                if member not in current_members:
                    current_members.append(member)
            await main.db("UPDATE user_groups SET can_post_room_reservation = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member added successfully", 200
        elif action == 'remove_can_post_room_reservation':
            if not subject or not isinstance(subject, list):
                return "Invalid user", 400
            current_members = await main.db("SELECT can_post_room_reservation FROM user_groups WHERE id = ?", (group_id,))
            current_members = current_members[0][0].split(',')
            for member in subject:
                if member in current_members:
                    current_members.remove(member)
            await main.db("UPDATE user_groups SET can_post_room_reservation = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member removed successfully", 200
        else:
            return "Invalid action", 400
    except Exception as e:
        print(f"An error occurred while modifying the group: {e}")
        return "Internal Server Error", 500

async def get_public_group_list(session_id):
    try:
        username = await main.users.get_username_from_session(session_id)
        if not username:
            return "Unauthorized", 401
        # return group id and group name in json format
        groups = await main.db("SELECT id, name FROM user_groups WHERE not_public = 0")
        return groups, 200
    except Exception as e:
        print(f"An error occurred while fetching the public group list: {e}")
        return "Internal Server Error", 500

async def join_public_group(session_id, group_id):
    try:
        current_user = await main.users.get_username_from_session(session_id)

        # Check if the group is public
        not_public = await main.db("SELECT not_public FROM user_groups WHERE id = ?", (group_id,))
        if not not_public:
            return "Group not found", 404
        elif not_public[0][0] != 0:
            return "Group is not public", 403

        # Get the current member list
        current_members = await main.db("SELECT member FROM user_groups WHERE id = ?", (group_id,))
        current_members = current_members[0]['member'].split(',')

        # Add the user to the member list if not already a member
        if current_user not in current_members:
            current_members.append(current_user)
            await main.db("UPDATE user_groups SET member = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Joined group successfully", 200
        else:
            return "User is already a member of the group", 400
    except Exception as e:
        print(f"An error occurred while joining the group: {e}")
        return "Internal Server Error", 500

async def leave_group(session_id, group_id):
    try:
        current_user = await main.users.get_username_from_session(session_id)

        # Get the current lists from the database
        group_data = await main.db("SELECT admin, can_post_announcement, can_post_assessment, can_post_pull, member FROM user_groups WHERE id = ?", (group_id,))
        if not group_data:
            return "Group not found", 404

        group_data = group_data[0]
        # return 403 if user is not in the group
        if current_user not in group_data[4].split(','):
            return "User is not a member of the group", 403

        # Remove the user from each list
        query = 'UPDATE user_groups SET'
        params = []
        columns = ["admin", "can_post_announcement", "can_post_assessment", "can_post_pull", "member"]
        for i in range(5):
            try:
                lst = group_data[i].split(',')
                if current_user in lst:
                    lst.remove(current_user)
                    query += f' {columns[i]} = ?,'
                    params.append(','.join(lst))
            except:
                pass

        query = query.rstrip(',') + ' WHERE id = ?'
        params.append(group_id)

        if len(params) == 1:
            return "User is not a member of the group", 403
        await main.db(query, tuple(params))
        return "Exited group successfully", 200
    except Exception as e:
        print(f"An error occurred while exiting the group: {e}")
        return "Internal Server Error", 500

async def get_post_permissions(session_id, group_id, post_type):
    try:
        username = await main.users.get_username_from_session(session_id)
        post_type = f'can_post_{post_type}'
        permission_list = await main.db("SELECT ? FROM user_groups WHERE id = ?", (post_type, group_id))
        permission_list = permission_list[0][0].split(',')
        if username in permission_list:
            return True
        else:
            return False


    except Exception as e:
        print(f"An error occurred while fetching the post permissions: {e}")
        return "Internal Server Error", 500