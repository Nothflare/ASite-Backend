import main
# permission in database is a list of group ids that can view the post (e.g. 1, 2, 3)

async def create_post(session_id, title, content, post_type, permission, post_as, label=None):
    try:
        # Retrieve the user's group from the session
        user = await main.users.get_username_from_session(session_id)
        user_groups = await main.db("SELECT `group` FROM users WHERE username = ?", (user,))

        if not any(group[0] == post_as for group in user_groups):
            return "Invalid 'post as' group given", 401

        # Verify that the user has permission to post the specified type
        user_group_id = post_as
        post_type_permission_column = f"can_post_{post_type}"
        permission_check_query = f"SELECT {post_type_permission_column} FROM user_groups WHERE id = ?"
        permission_result = await main.db(permission_check_query, (user_group_id,))

        if not permission_result or permission_result[0][0] == 0:
            return "User does not have permission to post this type", 403

        # Encode content, title, label
        content = content.encode('utf-8')
        title = title.encode('utf-8')
        if label:
            label = label.encode('utf-8')

        # Encode permission into string with post_as at the front
        permission_str = ",".join(map(str, [post_as] + sorted(permission)))

        # Insert the post into the database
        await main.db(
            "INSERT INTO posts (title, content, author, type, label, permission, post_as) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, content, user, post_type, label, permission_str, post_as)
        )

        if post_type == "pull":
            post_id = await main.db(
                "SELECT id FROM posts WHERE title = ? AND content = ? AND author = ? AND type = ? AND label = ? AND permission = ? AND post_as = ?",
                (title, content, user, post_type, label, permission_str, post_as)
            )
            await main.db("INSERT INTO pulls (post_id, agree, disagree) VALUES (?, 0, 0)", (post_id[0][0],))

        return "Post created successfully", 201

    except Exception as e:
        print(f"An error occurred while creating post: {e}")
        return "Internal Server Error", 500

async def get_my_posts(session_id, start_from=0):
    try:
        # Retrieve the user's group from the session
        user = await main.users.get_username_from_session(session_id)

        # Query the database to get the user's posts
        res = await main.db("SELECT id, title, author, label, created_at FROM posts WHERE author = ? LIMIT 30 OFFSET ?", (user, start_from))

        # Append the posts to the list
        posts = [{
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "label": row[3],
            "created_at": row[4]
        } for row in res]

        return {"posts": posts}, 200
    except Exception as e:
        print(f"An error occurred while fetching user's posts: {e}")
        return "Internal Server Error", 500


async def get_posts(session_id, post_type, start_from=0):
    if post_type == "my":
        return await get_my_posts(session_id, start_from)
    try:
        # Retrieve the user's group from the session
        user = await main.users.get_username_from_session(session_id)
        user_groups = await main.db("SELECT group FROM users WHERE username = ?", (user))
        if not user_groups:
            return "User group not found", 404

        # Convert user_groups to a list of group ids
        group_ids = [group[0] for group in user_groups]

        # Check if user is admin (group id = 1)
        if 1 in group_ids:
            # Query the database to get posts where the type is post_type
            res = await main.db("SELECT id, title, author, label, created_at FROM posts WHERE type = ? LIMIT 30 OFFSET ?", (post_type, start_from))
        else:
            # Query the database to get posts where the permission includes the user's group and type is post_type
            placeholders = ','.join('?' for _ in group_ids)
            query = f"""
                SELECT id, title, author, label, created_at 
                FROM posts 
                WHERE type = ? 
                AND (permission LIKE '%' || ? || '%' { ' OR permission LIKE '%' || ? || '%' ' * (len(group_ids) - 1) })
                LIMIT 30 OFFSET ?
            """
            res = await main.db(query, (post_type, *group_ids, start_from))

        # Append the posts to the list
        posts = [{
            "id": row[0],
            "title": row[1],
            "author": row[2],
            "label": row[3],
            "created_at": row[4]
        } for row in res]

        return {"posts": posts}, 200
    except Exception as e:
        print(f"An error occurred while fetching posts: {e}")
        return "Internal Server Error", 500

async def get_details(session_id, post_id):
    try:
        # Retrieve the user's group from the session
        user = await main.users.get_username_from_session(session_id)
        user_groups = await main.db("SELECT `group` FROM users WHERE username = ?", (user,))
        if not user_groups:
            return "User group not found", 404

        # Convert user_groups to a list of group ids
        group_ids = [group[0] for group in user_groups]

        # Query the database to get the post
        res = await main.db("SELECT id, title, author, label, created_at, content, permission, post_as FROM posts WHERE id = ?", (post_id,))
        if not res:
            return "Post not found", 404

        post = res[0]
        post_permission = list(map(int, post[6].split(',')))

        # Check if the user's group is in the post's permission or if the user is an admin
        if not any(group in post_permission for group in group_ids) and not 1 in group_ids:
            return "Unauthorized", 401

        # Return the post details
        return {
            "id": post[0],
            "title": post[1],
            "author": post[2],
            "label": post[3],
            "created_at": post[4],
            "content": post[5]
        }, 200
    except Exception as e:
        print(f"An error occurred while fetching post details: {e}")
        return "Internal Server Error", 500

async def get_pull_details(session_id, post_id):
    try:
        # Retrieve the user's group from the session
        user = await main.users.get_username_from_session(session_id)
        user_groups = await main.db("SELECT `group` FROM users WHERE username = ?", (user,))
        if not user_groups:
            return "User group not found", 404

        # Convert user_groups to a list of group ids
        group_ids = [group[0] for group in user_groups]

        # Query the database to get the post's permission
        res = await main.db("SELECT permission FROM posts WHERE id = ?", (post_id,))
        if not res:
            return "Post not found", 404

        post_permission = list(map(int, res[0][0].split(',')))

        # Check if the user's group is in the post's permission or if the user is an admin
        if not any(group in post_permission for group in group_ids) and not 1 in group_ids:
            return "Unauthorized", 401

        # Query the database to get the pull details
        res = await main.db("SELECT agree, disagree FROM pulls WHERE post_id = ?", (post_id,))
        if not res:
            return "Pull not found", 404

        # Return the pull details
        return {
            "agree": res[0][0],
            "disagree": res[0][1]
        }, 200
    except Exception as e:
        print(f"An error occurred while fetching pull details: {e}")
        return "Internal Server Error", 500

async def vote(session_id, post_id, opinion):
    try:
        # Retrieve the user's group from the session
        user = await main.users.get_username_from_session(session_id)
        user_groups = await main.db("SELECT `group` FROM users WHERE username = ?", (user,))
        if not user_groups:
            return "User group not found", 404

        # Convert user_groups to a list of group ids
        group_ids = [group[0] for group in user_groups]

        # Query the database to get the post's permission
        res = await main.db("SELECT permission FROM posts WHERE id = ?", (post_id,))
        if not res:
            return "Post not found", 404

        post_permission = list(map(int, res[0][0].split(',')))

        # Check if the user's group is in the post's permission or if the user is an admin
        if not any(group in post_permission for group in group_ids) and not 1 in group_ids:
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
        # Retrieve the user's group from the session
        user = await main.users.get_username_from_session(session_id)
        user_groups = await main.db("SELECT `group` FROM users WHERE username = ?", (user,))
        if not user_groups:
            return "User group not found", 404

        # Query the database to get the post's author
        res = await main.db("SELECT author FROM posts WHERE id = ?", (post_id,))
        if not res:
            return "Post not found", 404

        # Check if the user is the author
        if user != res[0][0]:
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

