import sqlite3
import os
from datetime import datetime
import streamlit as st

DB_PATH = "user_data.db"

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            signup_date TEXT,
            last_login TEXT
        )
    ''')
    
    # Create searches table
    c.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            timestamp TEXT,
            symbols TEXT,
            timeframes TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(username, name, email):
    """Add a new user to the database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    try:
        c.execute('''
            INSERT INTO users (username, name, email, signup_date, last_login)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, name, email, now, now))
        conn.commit()
    except sqlite3.IntegrityError:
        # User already exists, update last login
        c.execute('''
            UPDATE users
            SET last_login = ?
            WHERE username = ?
        ''', (now, username))
        conn.commit()
    finally:
        conn.close()

def log_search(username, symbols, timeframes):
    """Log a search operation"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    c.execute('''
        INSERT INTO searches (username, timestamp, symbols, timeframes)
        VALUES (?, ?, ?, ?)
    ''', (username, now, ','.join(symbols), ','.join(timeframes)))
    
    conn.commit()
    conn.close()

def get_user_stats(username):
    """Get user statistics"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get total searches
    c.execute('SELECT COUNT(*) FROM searches WHERE username = ?', (username,))
    total_searches = c.fetchone()[0]
    
    # Get most searched symbols
    c.execute('''
        SELECT symbols, COUNT(*) as count 
        FROM searches 
        WHERE username = ? 
        GROUP BY symbols 
        ORDER BY count DESC 
        LIMIT 5
    ''', (username,))
    top_symbols = c.fetchall()
    
    conn.close()
    return {
        'total_searches': total_searches,
        'top_symbols': top_symbols
    }

# Initialize the database when the module is imported
init_db()
