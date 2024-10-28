#Configurations from environment variables
from os import environ
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import timedelta

#Initialise Flask
app = Flask(__name__)
class Config:
    #Sessions Config
    app.config['SECRET_KEY'] = environ.get('SECRET_KEY')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

    # DB Config
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
    app.config['SQLALCHEMY_BINDS'] = {
        'auditLogs': 'sqlite:///auditLogs.db',
        'users': 'sqlite:///users.db',
        'devices': 'sqlite:///devices.db',
        'reservations': 'sqlite:///reservations.db'
    }