import os
import sqlite3
import configparser

config = configparser.ConfigParser()
config.read('config.conf')

DATABASE_PATH = config['database']['path']

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
                    status INTEGER DEFAULT 1
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
                    can_post_room_reservation TEXT NOT NULL,
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
            db.execute('''
                CREATE TABLE rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    open_time TIMESTAMP,
                    close_time TIMESTAMP,
                    available_days TEXT,
                    unavailable_periods TEXT,
                    status INTEGER DEFAULT 1
                )
            ''')
            db.execute('''
                CREATE TABLE reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER,
                    username TEXT,
                    for TEXT,
                    reason TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approval_status INTEGER DEFAULT 0,
                    approved_by TEXT,
                    FOREIGN KEY(room_id) REFERENCES rooms(id),
                    FOREIGN KEY(username) REFERENCES users(username),
                    FOREIGN KEY(approved_by) REFERENCES users(username)
                )
            ''')
            db.commit()

initialize_database()