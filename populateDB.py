from dbManager import database, Device, app  # Adjust import if needed to match your app structure
with app.app_context():
    # Initialize the database (only if needed, e.g., in Flask shell or initial setup)
    database.create_all()

    # Define sample data for two rooms, each with 5 PCs
    devices = [
        Device(hostname=f"PC-Room101-{i+1}", address=f"192.168.1.{i+1}", room="101", is_reserved=False)
        for i in range(5)
    ] + [
        Device(hostname=f"PC-Room102-{i+1}", address=f"192.168.2.{i+1}", room="102", is_reserved=False)
        for i in range(5)
    ]

    # Add devices to the session and commit to the database
    database.session.add_all(devices)
    database.session.commit()

    print("Database populated with 10 PCs.")
