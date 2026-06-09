import mysql.connector

# Connect to MySQL (update password if needed)
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='Password123@'  # Update with your MySQL root password
)

cursor = conn.cursor()

# Create database
cursor.execute('CREATE DATABASE IF NOT EXISTS accident_detection')

# Use database
cursor.execute('USE accident_detection')

# Create users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) UNIQUE,
        email VARCHAR(255),
        password_hash VARCHAR(255)
    )
''')

conn.commit()
cursor.close()
conn.close()

print('Database and table created successfully')
