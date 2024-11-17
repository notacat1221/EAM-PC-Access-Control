from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, inspect
app = Flask(__name__)
app.config.from_object('config.Config')
database = SQLAlchemy()
database.init_app(app)

def init_app(app):
    database.init_app(app)

def tablesCheck():
    # Creates each table one by one in the database
    with app.app_context():
        inspector = inspect(database.engine)  # Get the inspector for the engine
        for table in [User.__table__, Device.__table__, Reservation.__table__, AuditLog.__table__]:
            if not inspector.has_table(table.name):  # Use the inspector to check if the table exists
                table.create(database.engine)
                print(f"Table '{table.name}' created successfully.")
            else:
                print(f"Table '{table.name}' already exists.")



class User(database.Model):
    __tablename__ = 'users'

    username = database.Column(database.String(8), unique=True, nullable=False, primary_key=True)
    usertype = database.Column(database.String(20), nullable=False)
    password = database.Column(database.String(40), nullable=False)
    has_reservation = database.Column(database.Boolean, nullable=False)

class Device(database.Model):
    __tablename__ = 'devices'

    hostname = database.Column(database.String(20), unique=True, nullable=False, primary_key=True)
    address = database.Column(database.String(15), nullable=False)
    room = database.Column(database.String(4), nullable=False)
    is_reserved = database.Column(database.Boolean, nullable=False)

class Reservation(database.Model):
    __tablename__ = 'reservations'

    id = database.Column(database.Integer, primary_key=True)
    reserved_user = database.Column(database.String(20), nullable=False)
    reserved_device = database.Column(database.String(20), nullable=False)
    reserved_time = database.Column(DateTime(timezone=True), nullable=False)

class AuditLog(database.Model):
    __tablename__ = 'auditlogs'

    user_id = database.Column(database.String(8), database.ForeignKey('users.username'), primary_key=True)
    device_id = database.Column(database.String(20), database.ForeignKey('devices.hostname'), primary_key=True)
    caution_level = database.Column(database.String(20), nullable=False)
