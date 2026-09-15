import sqlite3
import os

import os

# Path to your actual SQLite database
shopfleetdb = 'instance/shopfleet.db'


# Connect to DB
conn = sqlite3.connect(shopfleetdb)
cursor = conn.cursor()

# Add username column if it doesn’t exist already
try:
    cursor.execute("ALTER TABLE Employees ADD COLUMN username TEXT;")
    print("✅ 'username' column added successfully to Employees table.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️ 'username' column already exists, skipping.")
    else:
        raise

conn.commit()
conn.close()
