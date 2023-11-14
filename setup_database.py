import sqlite3

connection = sqlite3.connect("finance.db")
cursor = connection.cursor()

# Create the users table
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    cash NUMERIC NOT NULL DEFAULT 10000.00
)
"""
)

connection.commit()
connection.close()
