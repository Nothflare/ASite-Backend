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
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bio TEXT,
                    profile_pic TEXT,
                    login_status INTEGER DEFAULT 0
                )
            ''')
            db.execute('''
                CREATE TABLE inactive_users (
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                )
            ''')
            db.execute('''
                CREATE TABLE posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    author INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(author) REFERENCES users(id)
                )
            ''')
            db.execute('''
                CREATE TABLE votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    user_id INTEGER,
                    vote INTEGER,
                    FOREIGN KEY(post_id) REFERENCES posts(id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            db.commit()

# Call this function at the start of your application
initialize_database()