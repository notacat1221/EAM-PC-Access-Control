import os
from datetime import timedelta
from cryptography.fernet import Fernet

class Config:
    # Sessions Config
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')  # Provide a default for local development

    WTF_CSRF_ENABLED = True  # Enable CSRF protection
    WTF_CSRF_SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')

    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_PERMANENT = False

    # MySQL Database Config
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://pymanager:%Pa55w0rd@10.0.10.4/mysqleam"

    default_key = Fernet.generate_key()
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', default_key)