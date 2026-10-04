import sqlite3

connection = sqlite3.connect("expense.db")
cursor = connection.cursor()

try:
    cursor.execute("""
        ALTER TABLE expenses
        ADD COLUMN user_id INTEGER
        REFERENCES users(id)
    """)

    connection.commit()

    print("user_id added successfully!")

except sqlite3.OperationalError as error:

    if "duplicate column name" in str(error):
        print("user_id already exists!")

    else:
        print("Migration error:", error)

connection.close()