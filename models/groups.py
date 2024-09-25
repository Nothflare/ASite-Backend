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
        return main.json.dumps(groups), 200
    except Exception as e:
        print(f"An error occurred while fetching the user's groups: {e}")
        return "Internal Server Error", 500

async def create_group(session_id, group_name, admin, not_public=0, can_post_announcement=[], can_post_assessment=[], can_post_pull=[], can_post_room_reservation=[], members=[]):
    try:
        current_user = await main.users.get_username_from_session(session_id)
        # Check if the user is admin
        is_admin = await main.db("SELECT * FROM user_groups WHERE id = ? AND member LIKE ?", (main.GLOBAL_ADMIN, '%' + current_user + '%',))
        if not is_admin:
            return "Unauthorized", 401

        # Insert the new group into the database
        await main.db('''
            INSERT INTO user_groups (name, admin, not_public, can_post_announcement, can_post_assessment, can_post_pull, can_post_room_reservation, member)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (group_name, admin, not_public, ','.join(can_post_announcement), ','.join(can_post_assessment), ','.join(can_post_pull), ','.join(can_post_room_reservation), ','.join(members)))

        return "Group created successfully", 201
    except Exception as e:
        print(f"An error occurred while creating the group: {e}")
        return "Internal Server Error", 500

async def modify_group(session_id, group_id, action, admin=None, not_public=None, can_post_announcement=None, can_post_assessment=None, can_post_pull=None, can_post_room_reservation=None, members=None):
    try:
        current_user = await main.users.get_username_from_session(session_id)
        # Check if the user is in the member list of the group with id = 1 or is admin in the current group
        is_admin = await main.db("""
            SELECT 1
            FROM user_groups
            WHERE (id = ? AND member LIKE ?)
               OR (id = ? AND admin = ?)
        """, (main.GLOBAL_ADMIN, '%' + current_user + '%', group_id, current_user))
        if not is_admin:
            return "Unauthorized", 401
        if action == 'delete':
            # Delete the group from the database
            await main.db("DELETE FROM user_groups WHERE id = ?", (group_id,))
            return "Group deleted successfully", 200
        elif action == 'visibility':
            # Update the visibility of the group
            await main.db("UPDATE user_groups SET not_public = ? WHERE id = ?", (not_public, group_id))
            return "Group visibility updated successfully", 200
        elif action == 'add_admin':
            # Add a new admin to the group (admin is a list of usernames)
            # Get the current admin list
            current_admin = await main.db("SELECT admin FROM user_groups WHERE id = ?", (group_id,))
            # Add the new admin to the list
            current_admin = current_admin[0]['admin'].split(',')
            current_admin.append(admin)
            # Update the admin list in the database
            await main.db("UPDATE user_groups SET admin = ? WHERE id = ?", (','.join(current_admin), group_id))
            return "Admin added successfully", 200
        elif action == 'remove_admin':
            # Remove an admin from the group (admin is a list of usernames)
            # Get the current admin list
            current_admin = await main.db("SELECT admin FROM user_groups WHERE id = ?", (group_id,))
            # Remove the admin from the list
            current_admin = current_admin[0]['admin'].split(',')
            current_admin.remove(admin)
            # Update the admin list in the database
            await main.db("UPDATE user_groups SET admin = ? WHERE id = ?", (','.join(current_admin), group_id))
            return "Admin removed successfully", 200
        elif action == 'add_member':
            # Add a new member to the group (members is a list of usernames)
            # Get the current member list
            current_members = await main.db("SELECT member FROM user_groups WHERE id = ?", (group_id,))
            # Add the new member to the list
            current_members = current_members[0]['member'].split(',')
            current_members.append(members)
            # Update the member list in the database
            await main.db("UPDATE user_groups SET member = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member added successfully", 200
        elif action == 'remove_member':
            # Remove a member from the group (members is a list of usernames)
            # Get the current member list
            current_members = await main.db("SELECT member FROM user_groups WHERE id = ?", (group_id,))
            # Remove the member from the list
            current_members = current_members[0]['member'].split(',')
            current_members.remove(members)
            # Update the member list in the database
            await main.db("UPDATE user_groups SET member = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member removed successfully", 200
        elif action == 'add_can_post_announcement':
            # Add a new member to the group (members is a list of usernames)
            # Get the current member list
            current_members = await main.db("SELECT can_post_announcement FROM user_groups WHERE id = ?", (group_id,))
            # Add the new member to the list
            current_members = current_members[0]['can_post_announcement'].split(',')
            current_members.append(can_post_announcement)
            # Update the member list in the database
            await main.db("UPDATE user_groups SET can_post_announcement = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member added successfully", 200
        elif action == 'remove_can_post_announcement':
            # Remove a member from the group (members is a list of usernames)
            # Get the current member list
            current_members = await main.db("SELECT can_post_announcement FROM user_groups WHERE id = ?", (group_id,))
            # Remove the member from the list
            current_members = current_members[0]['can_post_announcement'].split(',')
            current_members.remove(can_post_announcement)
            # Update the member list in the database
            await main.db("UPDATE user_groups SET can_post_announcement = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member removed successfully", 200
        elif action == 'add_can_post_assessment':
            # Add a new member to the group (members is a list of usernames)
            # Get the current member list
            current_members = await main.db("SELECT can_post_assessment FROM user_groups WHERE id = ?", (group_id,))
            # Add the new member to the list
            current_members = current_members[0]['can_post_assessment'].split(',')
            current_members.append(can_post_assessment)
            # Update the member list in the database
            await main.db("UPDATE user_groups SET can_post_assessment = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member added successfully", 200
        elif action == 'remove_can_post_assessment':
            # Remove a member from the group (members is a list of usernames)
            # Get the current member list
            current_members = await main.db("SELECT can_post_assessment FROM user_groups WHERE id = ?", (group_id,))
            # Remove the member from the list
            current_members = current_members[0]['can_post_assessment'].split(',')
            current_members.remove(can_post_assessment)
            # Update the member list in the database
            await main.db("UPDATE user_groups SET can_post_assessment = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member removed successfully", 200
        elif action == 'add_can_post_pull':
            # Add a new member to the group (members is a list of usernames)
            # Get the current member list
            current_members = await main.db("SELECT can_post_pull FROM user_groups WHERE id = ?", (group_id,))
            # Add the new member to the list
            current_members = current_members[0]['can_post_pull'].split(',')
            current_members.append(can_post_pull)
            # Update the member list in the database
            await main.db("UPDATE user_groups SET can_post_pull = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member added successfully", 200
        elif action == 'remove_can_post_pull':
            # Remove a member from the group (members is a list of usernames)
            # Get the current member list
            current_members = await main.db("SELECT can_post_pull FROM user_groups WHERE id = ?", (group_id,))
            # Remove the member from the list
            current_members = current_members[0]['can_post_pull'].split(',')
            current_members.remove(can_post_pull)
            # Update the member list in the database
            await main.db("UPDATE user_groups SET can_post_pull = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member removed successfully", 200
        elif action == 'add_can_post_room_reservation':
            # Add a new member to the group (members is a list of usernames)
            # Get the current member list
            current_members = await main.db("SELECT can_post_room_reservation FROM user_groups WHERE id = ?", (group_id,))
            # Add the new member to the list
            current_members = current_members[0]['can_post_room_reservation'].split(',')
            current_members.append(can_post_room_reservation)
            # Update the member list in the database
            await main.db("UPDATE user_groups SET can_post_room_reservation = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member added successfully", 200
        elif action == 'remove_can_post_room_reservation':
            # Remove a member from the group (members is a list of usernames)
            # Get the current member list
            current_members = await main.db("SELECT can_post_room_reservation FROM user_groups WHERE id = ?", (group_id,))
            # Remove the member from the list
            current_members = current_members[0]['can_post_room_reservation'].split(',')
            current_members.remove(can_post_room_reservation)
            # Update the member list in the database
            await main.db("UPDATE user_groups SET can_post_room_reservation = ? WHERE id = ?", (','.join(current_members), group_id))
            return "Member removed successfully", 200
        else:
            return "Invalid action", 400
    except Exception as e:
        print(f"An error occurred while modifying the group: {e}")
        return "Internal Server Error", 500

async def get_public_group_list():
    try:
        # return group id and group name in json format
        groups = await main.db("SELECT id, name FROM user_groups WHERE not_public = 0")
        # Convert the result to JSON format
        return main.json.dumps(groups), 200
    except Exception as e:
        print(f"An error occurred while fetching the public group list: {e}")
        return "Internal Server Error", 500

async def join_public_group(session_id, group_id):
    try:
        current_user = await main.users.get_username_from_session(session_id)

        # Check if the group is public
        is_public = await main.db("SELECT 1 FROM user_groups WHERE id = ? AND not_public = 0", (group_id,))
        if not is_public:
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

async def exit_group(session_id, group_id):
    try:
        current_user = await main.users.get_username_from_session(session_id)

        # Get the current lists from the database
        group_data = await main.db("SELECT admin, can_post_announcement, can_post_assessment, can_post_pull, member FROM user_groups WHERE id = ?", (group_id,))
        if not group_data:
            return "Group not found", 404

        group_data = group_data[0]
        # return 403 if user is not in the group
        if current_user not in group_data['member']:
            return "User is not a member of the group", 403
        # Remove the user from each list
        for key in ['admin', 'can_post_announcement', 'can_post_assessment', 'can_post_pull', 'member']:
            if group_data[key]:
                members_list = group_data[key].split(',')
                if current_user in members_list:
                    members_list.remove(current_user)
                    group_data[key] = ','.join(members_list)
                else:
                    group_data[key] = ','.join(members_list)

        # Update the database with the modified lists
        await main.db("""
            UPDATE user_groups
            SET admin = ?, can_post_announcement = ?, can_post_assessment = ?, can_post_pull = ?, member = ?
            WHERE id = ?
        """, (group_data['admin'], group_data['can_post_announcement'], group_data['can_post_assessment'], group_data['can_post_pull'], group_data['member'], group_id))

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

