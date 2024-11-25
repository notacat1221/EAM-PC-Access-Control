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
        for table in [User.__table__, Device.__table__, Reservation.__table__, AuditLog.__table__, Room.__table__, Timetable.__table__]:
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
    eam_enrolled = database.Column(database.Boolean, nullable=False)

    # Required methods for flask-login
    def is_active(self):
        return True
    def get_id(self):
        return self.username
    def is_authenticated(self):
        return True
    def is_anonymous(self):
        return False


class Device(database.Model):
    __tablename__ = 'devices'

    hostname = database.Column(database.String(20), unique=True, nullable=False, primary_key=True)
    address = database.Column(database.String(15), nullable=False)
    room = database.Column(database.String(4), database.ForeignKey('rooms.room_number'), nullable=False)
    eam_assigned_student = database.Column(database.String(8), nullable=True)

class Reservation(database.Model):
    __tablename__ = 'reservations'

    user_id = database.Column(database.String(8), database.ForeignKey('users.username'), primary_key=True)
    hostname = database.Column(database.String(20), unique=True, nullable=False, primary_key=True)
    room_number = database.Column(database.String(4), database.ForeignKey('rooms.room_number'), nullable=False)
    start_time = database.Column(database.Time, nullable=False)
    end_time = database.Column(database.Time, nullable=False)

class AuditLog(database.Model):
    __tablename__ = 'auditlogs'

    user_id = database.Column(database.String(8), database.ForeignKey('users.username'), primary_key=True)
    device_id = database.Column(database.String(20), database.ForeignKey('devices.hostname'), primary_key=True)
    caution_level = database.Column(database.String(20), nullable=False)

class Room(database.Model):
    __tablename__ = 'rooms'

    room_number = database.Column(database.String(4), primary_key=True)
    eam_room = database.Column(database.Boolean, nullable=False)

class Timetable(database.Model):
    __tablename__ = 'timetable'

    id = database.Column(database.Integer, primary_key=True)
    room_number = database.Column(database.String(4), database.ForeignKey('rooms.room_number'), nullable=False)
    day_of_week = database.Column(database.String(9), nullable=False)  # e.g., "Monday", "Tuesday"
    start_time = database.Column(database.Time, nullable=False)
    end_time = database.Column(database.Time, nullable=False)




