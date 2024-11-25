import os
from datetime import timedelta


class Config:
    # Sessions Config
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')  # Provide a default for local development
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_PERMANENT = False

    # MySQL Database Config
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://PyManager:%Pa55w0rd@localhost/MYSQLEAM"

    # Example of using MySQL for additional binds
    SQLALCHEMY_BINDS = {
        'auditlogs': 'mysql+pymysql://PyManager:%Pa55w0rd@localhost/auditLogs',
        'users': 'mysql+pymysql://PyManager:%Pa55w0rd@localhost/users',
        'devices': 'mysql+pymysql://PyManager:%Pa55w0rd@localhost/devices',
        'reservations': 'mysql+pymysql://PyManager:%Pa55w0rd@localhost/reservations'
    }

