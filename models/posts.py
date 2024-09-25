import main

# permission in database is a list of group ids that can view the post (e.g. 1, 2, 3)
# permission = None means everyone can view the post
# every post must have a post_as group id
# post_as group id must be in the permission list
# post_as group id must be in the user's group list
# admin can view all posts
# admin can edit all posts
# admin can delete all posts
# admin can vote on all posts
# only the author can edit or delete a post

async def create_post(session_id, title, content, post_type, permission, post_as, start_at = None, end_at = None, label = None):
    try:
        # Retrieve the user's group from the session
        user = await main.users.get_username_from_session(session_id)
        user_groups = await main.groups.get_user_groups(session_id)
        # Converting user_groups to a list of group ids
        group_ids = [group[0] for group in user_groups]

        # Check if post_as group id is in the user's group list
        if post_as not in group_ids:
            return "Unauthorized", 401
        if not main.groups.get_post_permissions(session_id, post_as, post_type):
            return "Unauthorized", 401
        # If permission is not None, check if post_as group id is in the permission list
        if permission is not None:
            permission_list = [int(group_id.strip()) for group_id in permission.split(',')]
            if post_as not in permission_list:
                permission_list.append(post_as)
            # encode into list
            permission = ",".join([str(group_id) for group_id in permission_list])
        # Insert the post into the database
        await main.db("""
            INSERT INTO posts (title, content, post_type, permission, post_as, label, author, start_at, end_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, content, post_type, permission, post_as, label, user, start_at, end_at))
        if post_type == "pull":
            post_id = await main.db("SELECT id FROM posts WHERE author = ? AND created_at = (SELECT MAX(created_at) FROM posts WHERE author = ?)", (user, user))
            await main.db("INSERT INTO pulls (post_id) VALUES (?)", (post_id[0][0],))
        return "Post created successfully", 201
    except Exception as e:
        print(f"An error occurred while creating the post: {e}")
        return "Internal Server Error", 500

async def get_posts(session_id, post_type, start_from=0, view_type='public', id=None, admin=False):
    try:
        if admin:
            username = await main.users.get_username_from_session(session_id)
            is_admin = await main.users.check_if_user_is_admin(username, 'global')
            if not is_admin:
                return "Unauthorized", 401
        if view_type == 'public':
            res = await main.db("SELECT id, title, author, label, created_at, start_at, end_at, post_as FROM posts WHERE post_type = ? AND permission IS NULL LIMIT 30 OFFSET ?", (post_type, start_from))
        elif view_type == 'my':
            user = await main.users.get_username_from_session(session_id)
            res = await main.db("SELECT id, title, author, label, created_at, start_at, end_at, post_as FROM posts WHERE author = ? AND post_type = ? LIMIT 30 OFFSET ?", (user, post_type, start_from))
        elif view_type == 'user' and id:
            if admin:
                res = await main.db("SELECT id, title, author, label, created_at, start_at, end_at, post_as FROM posts WHERE author = ? AND post_type = ? LIMIT 30 OFFSET ?", (id, post_type, start_from))
            else:
                res = await main.db("SELECT id, title, author, label, created_at, start_at, end_at, post_as FROM posts WHERE author = ? AND post_type = ? AND (permission IS NULL OR EXISTS (SELECT 1 FROM json_each(permission) WHERE value IN (?))) LIMIT 30 OFFSET ?", (id, post_type, ','.join(map(str, group_ids)), start_from))
        elif view_type == 'group' and id:
            if admin:
                res = await main.db("SELECT id, title, author, label, created_at, start_at, end_at, post_as FROM posts WHERE post_as = ? AND post_type = ? LIMIT 30 OFFSET ?", (id, post_type, start_from))
            else:
                res = await main.db("SELECT id, title, author, label, created_at, start_at, end_at, post_as FROM posts WHERE post_as = ? AND post_type = ? AND (permission IS NULL OR EXISTS (SELECT 1 FROM json_each(permission) WHERE value IN (?))) LIMIT 30 OFFSET ?", (id, post_type, ','.join(map(str, group_ids)), start_from))
        else:
            return "Invalid view type or missing id", 400

        posts = [{
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "label": row[3],
            "created_at": row[4],
            "start_at": row[5],
            "end_at": row[6],
            "post_as": row[7]
        } for row in res]

        return {"posts": posts}, 200
    except Exception as e:
        print(f"An error occurred while fetching posts: {e}")
        return "Internal Server Error", 500

async def get_details(session_id, post_id):
    try:
        # Query the database to get the post's permission
        res = await main.db("SELECT permission FROM posts WHERE id = ?", (post_id,))
        if not res:
            return "Post not found", 404
        if not res[0][0] is None:
            user_groups = await main.groups.get_user_groups(session_id)
            # Converting user_groups to a list of group ids
            group_ids = [group[0] for group in user_groups]
            post_permission = list(map(int, res[0][0].split(',')))
            # Check if the user's group is in the post's permission or if the user is an admin
            if not any(group in post_permission for group in group_ids) and not not main.GLOBAL_ADMIN in group_ids:
                return "Unauthorized", 401

        # Query the database to get all post details
        res = await main.db("SELECT * FROM posts WHERE id = ?", (post_id,))
        if not res:
            return "Post not found", 404

        # Assuming the columns are known and fixed, map them to a dictionary
        post_details = {
            "id": res[0][0],
            "title": res[0][1],
            "author": res[0][2],
            "label": res[0][3],
            "created_at": res[0][4],
            "start_at": res[0][5],
            "end_at": res[0][6],
            "post_as": res[0][7],
            "content": res[0][8],
            "permission": res[0][9]
            # Add other columns as needed
        }

        return post_details, 200
    except Exception as e:
        print(f"An error occurred while fetching post details: {e}")
        return "Internal Server Error", 500


async def get_pull_details(session_id, post_id):
    try:
        # Query the database to get the pull's permission, agree, and disagree counts
        res = await main.db("SELECT permission, agree, disagree FROM pulls WHERE post_id = ?", (post_id,))
        if not res:
            return "Post not found", 404

        # Check if the pull has specific permissions
        if res[0][0] is not None:
            user_groups = await main.groups.get_user_groups(session_id)
            # Converting user_groups to a list of group ids
            group_ids = [group[0] for group in user_groups]
            post_permission = list(map(int, res[0][0].split(',')))

            # Check if the user's group is in the pull's permission or if the user is an admin
            if not any(group in post_permission for group in group_ids) and not main.GLOBAL_ADMIN in group_ids:
                return "Unauthorized", 401

        pull_details = {
            "agree": res[0][1],
            "disagree": res[0][2]
        }

        return pull_details, 200
    except Exception as e:
        print(f"An error occurred while fetching pull details: {e}")
        return "Internal Server Error", 500

async def vote(session_id, post_id, opinion):
    try:
        # Query the database to get the pull's permission
        res = await main.db("SELECT permission FROM pulls WHERE post_id = ?", (post_id,))
        if not res:
            return "Post not found", 404

        # Check if the pull has specific permissions
        if res[0][0] is not None:
            user_groups = await main.groups.get_user_groups(session_id)
            # Converting user_groups to a list of group ids
            group_ids = [group[0] for group in user_groups]
            post_permission = list(map(int, res[0][0].split(',')))
            # Check if the user's group is in the pull's permission or if the user is an admin
            if not any(group in post_permission for group in group_ids) and not main.GLOBAL_ADMIN in group_ids:
                return "Unauthorized", 401

        # Update the vote count based on the opinion
        if opinion == "agree":
            await main.db("UPDATE pulls SET agree = agree + 1 WHERE post_id = ?", (post_id,))
        elif opinion == "disagree":
            await main.db("UPDATE pulls SET disagree = disagree + 1 WHERE post_id = ?", (post_id,))
        else:
            return "Invalid opinion", 400

        return "Vote submitted successfully", 200

    except Exception as e:
        print(f"An error occurred while submitting vote: {e}")
        return "Internal Server Error", 500

async def modify_post(session_id, post_id, action, title=None, content=None, label=None, permission=None):
    try:
        # Query the database to get the post's permission
        res = await main.db("SELECT permission FROM posts WHERE id = ?", (post_id,))
        if not res:
            return "Post not found", 404
        if not res[0][0] is None:
            user_groups = await main.groups.get_user_groups(session_id)
            # Converting user_groups to a list of group ids
            group_ids = [group[0] for group in user_groups]
            post_permission = list(map(int, res[0][0].split(',')))
            # Check if the user's group is in the post's permission or if the user is an admin
            if not any(group in post_permission for group in group_ids) and not main.GLOBAL_ADMIN in group_ids:
                return "Unauthorized", 401

        # Perform the requested action
        if action == "edit":
            if title:
                await main.db("UPDATE posts SET title = ? WHERE id = ?", (title, post_id))
            if content:
                await main.db("UPDATE posts SET content = ? WHERE id = ?", (content, post_id))
            if label:
                await main.db("UPDATE posts SET label = ? WHERE id = ?", (label, post_id))
            if permission:
                permission_str = ",".join(map(str, sorted(permission)))
                await main.db("UPDATE posts SET permission = ? WHERE id = ?", (permission_str, post_id))
            return "Post updated successfully", 200
        elif action == "delete":
            await main.db("DELETE FROM posts WHERE id = ?", (post_id))
            return "Post deleted successfully", 200
        else:
            return "Invalid action", 400

    except Exception as e:
        print(f"An error occurred while modifying the post: {e}")
        return "Internal Server Error", 500

async def follow_post(session_id, post_id):
    try:
        # Query the database to get the post's permission
        res = await main.db("SELECT permission FROM posts WHERE id = ?", (post_id,))
        if not res:
            return "Post not found", 404
        if not res[0][0] is None:
            user_groups = await main.groups.get_user_groups(session_id)
            # Converting user_groups to a list of group ids
            group_ids = [group[0] for group in user_groups]
            post_permission = list(map(int, res[0][0].split(',')))
            # Check if the user's group is in the post's permission or if the user is an admin
            if not any(group in post_permission for group in group_ids) and not main.GLOBAL_ADMIN in group_ids:
                return "Unauthorized", 401
        # add post_id to user's following_posts(a list of post ids)
        user = await main.users.get_username_from_session(session_id)
        # check if post_id is already in following_posts
        following_posts = await main.db("SELECT following_posts FROM users WHERE username = ?", (user,))
        following_posts = following_posts[0][0]
        if post_id in following_posts:
            return "Post already followed", 200
        following_posts.append(post_id)
        following_posts = ",".join([str(post_id) for post_id in following_posts])
        await main.db("UPDATE users SET following_posts = ? WHERE username = ?", (following_posts, user))
        return "Post followed successfully", 200
    except Exception as e:
        print(f"An error occurred while fetching post details: {e}")
        return "Internal Server Error", 500

async def get_timeline(session_id):
    # return all start and stop time that in user's following_posts (announcements and assessments)
    try:
        user = await main.users.get_username_from_session(session_id)
        following_posts = await main.db("SELECT following_posts FROM users WHERE username = ?", (user,))
        following_posts = following_posts[0][0]
        if not following_posts:
            return "No posts found", 404
        res = await main.db("SELECT id, title, label, start_at, end_at, post_as FROM posts WHERE id IN (?)", (following_posts,))
        if not res:
            return "No posts found", 404
        posts = [{
            "id": row[0],
            "title": row[1],
            "created_at": row[2],
            "start_at": row[3],
            "end_at": row[4],
            "post_as": row[5]
        } for row in res]
        return {"posts": posts}, 200
    except Exception as e:
        print(f"An error occurred while fetching posts: {e}")
        return "Internal Server Error", 500