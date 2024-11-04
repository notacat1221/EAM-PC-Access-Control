from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
import mysql.connector
from mysql.connector import Error
app = Flask(__name__)
app.config.from_object('config.Config')
database = SQLAlchemy()
database.init_app(app)

def init_app(app):
    database.init_app(app)

def create_all():
    with app.app_context():
        database.create_all()
def create_connection():
    try:
        # Replace 'MYSQL-EAM' with your named pipe name
        connection = mysql.connector.connect(
            user='Pypeline',                      # Your MySQL username
            password='%Pa55w0rd',         # Your MySQL password
            unix_socket='MYSQL-EAM',          # Named pipe (or UNIX socket on UNIX systems)
            database='MYSQLEAM'     # Optional: specify a database to use
        )

        if connection.is_connected():
            print("Connection to MySQL DB successful")
            return connection

    except Error as e:
        print(f"Error: '{e}'")
        return None

class User(database.Model):
    username = database.Column(database.String(20), unique=True, nullable=False, primary_key=True)
    usertype = database.Column(database.String(20), nullable=False)
    has_reservation = database.Column(database.Boolean, nullable=False)

class Device(database.Model):
    hostname = database.Column(database.String(20), unique=True, nullable=False, primary_key=True)
    address = database.Column(database.String(15), nullable=False)
    room = database.Column(database.String(4), nullable=False)
    is_reserved = database.Column(database.Boolean, nullable=False)

class Reservation(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    reserved_user = database.Column(database.String(20), nullable=False)
    reserved_device = database.Column(database.String(20), nullable=False)
    reserved_time = database.Column(DateTime(timezone=True), nullable=False)

class AuditLog(database.Model):
    user_id = database.Column(database.String(20), database.ForeignKey('users.username'), primary_key=True)
    device_id = database.Column(database.String(20), database.ForeignKey('devices.hostname'), primary_key=True)
    caution_level = database.Column(database.String(20), nullable=False)

create_connection()