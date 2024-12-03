from dbManager import database, Device, User, Timetable, app  # Ensure correct imports
from flask_bcrypt import Bcrypt
from sqlalchemy import text
import random
from datetime import datetime, timedelta, time
bcrypt = Bcrypt(app)
def populate_timetable():
    """
    Populate the timetable table in the database with random lessons.
    Each room will have four lessons per day (2 one-hour and 2 two-hour lessons).
    Lessons are randomly scheduled between 8:00 AM and 4:00 PM, avoiding overlaps.
    """
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    rooms = ['1', '2']
    lesson_durations = [timedelta(hours=1), timedelta(hours=2)]

    with app.app_context():
        for room in rooms:
            for day in days_of_week:
                lessons = []  # List to track lessons for the day

                while len(lessons) < 4:
                    start_hour = random.choice(range(9, 16))  # Lessons start between 9 AM and 4 PM
                    start_minute = random.choice([0, 30])    # Lessons start on the hour or half-hour
                    start_time = time(start_hour, start_minute)

                    # Select a random lesson duration
                    duration = random.choice(lesson_durations)
                    start_datetime = datetime.combine(datetime.today(), start_time)
                    end_datetime = start_datetime + duration
                    end_time = end_datetime.time()

                    # Check for overlaps with existing lessons
                    overlap = False
                    for lesson in lessons:
                        # Check if the new lesson overlaps with any existing lesson
                        # A lesson overlaps if its start time is during or after an existing lesson's start time
                        # and its end time is before or after the existing lesson's end time.
                        if (start_time >= lesson['start_time'] and start_time < lesson['end_time']) or \
                           (end_time > lesson['start_time'] and end_time <= lesson['end_time']) or \
                           (start_time < lesson['start_time'] and end_time > lesson['start_time']):
                            overlap = True
                            break

                    if not overlap:
                        lessons.append({
                            'room_number': room,
                            'day_of_week': day,
                            'start_time': start_time,
                            'end_time': end_time
                        })

                # Insert lessons into the database
                for lesson in lessons:
                    new_entry = Timetable(
                        room_number=lesson['room_number'],
                        day_of_week=lesson['day_of_week'],
                        start_time=lesson['start_time'],
                        end_time=lesson['end_time']
                    )
                    database.session.add(new_entry)
        database.session.commit()

    print("Timetable populated successfully.")



def insert_devices():
    devices = []
    for i in range(1, 6):
        # Devices for Room 1
        hostname = f"Room1-PC{i}"
        address = f"192.168.1.{i}"
        devices.append({"hostname": hostname, "address": address, "room": 1, "is_reserved": False})

        # Devices for Room 2
        hostname = f"Room2-PC{i}"
        address = f"192.168.2.{i}"
        devices.append({"hostname": hostname, "address": address, "room": 2, "is_reserved": False})

    # Raw SQL query for inserting devices
    query = """
        INSERT INTO devices (hostname, address, room, is_reserved)
        VALUES (:hostname, :address, :room, :is_reserved)
    """

    # Ensure the database operations are within the Flask app context
    with app.app_context():
        with database.engine.connect() as connection:
            with connection.begin():  # Begin a transaction
                # Execute bulk insert
                connection.execute(text(query), devices)

    print("10 devices added successfully.")

def add_users_to_database():
    # Prepare a list of values to insert
    users = []
    for x in 'abcd':
        for i in range(50):
            username = f"{x}{str(i).zfill(7)}"  # 7 digits after the letter
            password_hash = bcrypt.generate_password_hash('password').decode('utf-8')
            print(username, password_hash)
            users.append((username, password_hash, 'student', False, False))

    # Use raw SQL to insert in bulk
    query = """
        INSERT INTO users (username, password, usertype, has_reservation, eam_enrolled)
        VALUES (:username, :password, :usertype, :has_reservation, :eam_enrolled)
    """

    # Ensure the database operations are within the Flask app context
    with app.app_context():
        with database.engine.connect() as connection:
            with connection.begin():  # Begin a transaction
                # Execute bulk insert
                connection.execute(text(query), [{"username": username, "password": password_hash, "usertype": usertype, "has_reservation": has_reservation, "eam_enrolled": eam_enrolled} for username, password_hash, usertype, has_reservation, eam_enrolled in users])

    print("1000 users added successfully.")

# Call the function to add users
add_users_to_database()
