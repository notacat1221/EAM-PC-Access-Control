from dbManager import database, Device, User, app  # Ensure correct imports
from passlib.handlers.sha2_crypt import sha256_crypt
from sqlalchemy import text

def insert_devices():
    # Prepare a list of devices to insert
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
    password_hash = sha256_crypt.hash("password")  # Precompute the hash for efficiency
    for x in "abcd":
        for i in range(250):  # 250 users for each letter to make 1000 total
            username = f"{x}{str(i).zfill(7)}"  # Ensures 7 digits after the letter
            users.append((username, password_hash, "student", False))

    # Use raw SQL to insert in bulk
    query = """
        INSERT INTO users (username, password, usertype, is_reserved)
        VALUES (:username, :password, :usertype, :is_reserved)
    """

    # Ensure the database operations are within the Flask app context
    with app.app_context():
        with database.engine.connect() as connection:
            with connection.begin():  # Begin a transaction
                # Execute bulk insert
                connection.execute(text(query), [{"username": username, "password": password_hash, "usertype": "student", "is_reserved": False} for username, password_hash, usertype, is_reserved in users])

    print("1000 users added successfully.")

# Call the function to add users
insert_devices()
