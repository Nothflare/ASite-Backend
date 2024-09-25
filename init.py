import os
import sqlite3
import configparser

config = configparser.ConfigParser()
config.read('config.conf')

DATABASE_PATH = config['database']['path']

'''
database format:
- users
    - id
    - username
    - password
    - email
    - created_at
    - updated_at
    - bio
    - following_posts
    - status
- user_groups
    - id
    - name
    - admin
    - not_public (0 or 1) - 0 means public(default), 1 means private
    - can_post_announcement
    - can_post_assessment
    - can_post_pull
    - member
- unverified_users
    - username
    - password
    - email
    - created_at
- posts
    - id
    - title
    - content
    - author
    - type
    - label
    - permission
    - post_as
    - start_at
    - end_at
    - created_at
    - updated_at
-pulls
    - post_id
    - agree
    - disagree
'''

def initialize_database():
    if not os.path.exists(DATABASE_PATH):
        with sqlite3.connect(DATABASE_PATH) as db:
            db.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bio TEXT,
                    following_posts TEXT,
                    status INTEGER DEFAULT 0,
                    FOREIGN KEY (group) REFERENCES user_groups(id)
                )
            ''')
            db.execute('''
                CREATE TABLE user_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    admin TEXT NOT NULL,
                    not_public INTEGER DEFAULT 0,
                    can_post_announcement TEXT NOT NULL,
                    can_post_assessment TEXT NOT NULL,
                    can_post_pull TEXT NOT NULL,
                    member TEXT NOT NULL
                )
            ''')
            db.execute('''
                CREATE TABLE unverified_users (
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            db.execute('''
                CREATE TABLE posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    author INTEGER,
                    type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    permission TEXT,
                    post_as TEXT NOT NULL,
                    start_at TIMESTAMP,
                    end_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(author) REFERENCES users(id)
                )
            ''')
            db.execute('''
                CREATE TABLE pulls (
                    post_id INTEGER,
                    agree INTEGER,
                    disagree INTEGER,
                    FOREIGN KEY(post_id) REFERENCES posts(id)
                )
            ''')
            db.commit()

# Call this function at the start of your application
initialize_database()