from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect

app = Flask(__name__)
app.config.from_object('config.Config')
database = SQLAlchemy()
database.init_app(app)

def init_app(app):
    database.init_app(app)

def tablesCheck():
    # Required fields for each table
    required_fields = {
        'users': ['username', 'usertype', 'password', 'has_reservation', 'eam_enrolled'],
        'devices': ['hostname', 'address', 'room_number', 'eam_assigned_student'],
        'reservations': ['user_id', 'hostname', 'room_number', 'start_time', 'end_time', 'date'],
        'auditlogs': ['user_id', 'device_id', 'caution_level'],
        'rooms': ['room_number', 'eam_room'],
        'timetable': ['id', 'room_number', 'day_of_week', 'start_time', 'end_time']
    }

    with app.app_context():
        inspector = inspect(database.engine)  # Get the inspector for the engine
        for table in [User.__table__, Device.__table__, Reservation.__table__, AuditLog.__table__, Room.__table__, Timetable.__table__]:
            if not inspector.has_table(table.name):  # Use the inspector to check if the table exists
                table.create(database.engine)
                print(f"Table '{table.name}' created successfully.")
            else:
                print(f"Table '{table.name}' already exists.")
                # Check if all required fields are present
                columns = inspector.get_columns(table.name)
                column_names = [col['name'] for col in columns]
                missing_fields = [field for field in required_fields[table.name] if field not in column_names]
                if missing_fields:
                    print(f"Table '{table.name}' is missing fields: {', '.join(missing_fields)}.")
                else:
                    print(f"Table '{table.name}' has all required fields.")

class User(database.Model):
    __tablename__ = 'users'

    username = database.Column(database.String(8), unique=True, nullable=False, primary_key=True)
    usertype = database.Column(database.String(20), nullable=False)
    password = database.Column(database.String(40), nullable=False)
    has_reservation = database.Column(database.Boolean, nullable=False)
    eam_enrolled = database.Column(database.Boolean, nullable=False)

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
    room_number = database.Column(database.String(4), database.ForeignKey('rooms.room_number'), nullable=False)
    eam_assigned_student = database.Column(database.String(8), nullable=True)

    room = database.relationship('Room', backref='devices')

class Reservation(database.Model):
    __tablename__ = 'reservations'

    user_id = database.Column(database.String(8), database.ForeignKey('users.username'), primary_key=True)
    hostname = database.Column(database.String(20)  , nullable=False)
    room_number = database.Column(database.String(4), database.ForeignKey('rooms.room_number'), nullable=False)
    start_time = database.Column(database.Time, nullable=False)
    end_time = database.Column(database.Time, nullable=False)
    date = database.Column(database.Date, nullable=False)

    __table_args__ = (database.UniqueConstraint('user_id', 'hostname', name='uid_hostname_constraint'),)

class AuditLog(database.Model):
    __tablename__ = 'auditlogs'

    user_id = database.Column(database.String(8), database.ForeignKey('users.username'), primary_key=True)
    device_id = database.Column(database.String(20), database.ForeignKey('devices.hostname'), primary_key=True)
    action = database.Column(database.String(20), nullable=False)
    description = database.Column(database.String(255), nullable=False)
    timestamp = database.Column(database.DateTime, nullable=False)

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

