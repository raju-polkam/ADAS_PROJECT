import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'your_mysql_password' # Update with your MySQL root password if set
    MYSQL_DB = 'accident_detection'
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'your-email@example.com'
    MAIL_PASSWORD = 'your-email-password'
    ADMIN_EMAIL = 'admin@example.com'
    EMERGENCY_EMAILS = ['emergency1@example.com', 'emergency2@example.com']
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID') or 'YOUR_TWILIO_ACCOUNT_SID'
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN') or 'YOUR_TWILIO_AUTH_TOKEN'
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER') or 'YOUR_TWILIO_PHONE_NUMBER'   
    EMERGENCY_PHONE_NUMBERS = ['YOUR_EMERGENCY_PHONE_NUMBER']
