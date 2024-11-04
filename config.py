import os
from datetime import timedelta


class Config:
    # Sessions Config
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')  # Provide a default for local development
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # MySQL Database Config
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://Pypeline:%Pa55w0rd@localhost/MySQLEAM'

    # Example of using MySQL for additional binds
    SQLALCHEMY_BINDS = {
        'auditLogs': 'mysql+pymysql://Pypeline:%Pa55w0rd@localhost/auditLogs',
        'users': 'mysql+pymysql://Pypeline:%Pa55w0rd@localhost/users',
        'devices': 'mysql+pymysql://Pypeline:%Pa55w0rd@localhost/devices',
        'reservations': 'mysql+pymysql://Pypeline:%Pa55w0rd@localhost/reservations'
    }
