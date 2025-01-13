from flask import Flask, url_for, request, redirect, render_template, session, flash
from flask_login import LoginManager, login_user, login_required, current_user
from flask_bcrypt import Bcrypt

from cryptography.fernet import Fernet
import base64

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired

from flask_socketio import SocketIO
from flask_httpauth import HTTPBasicAuth

from urllib.parse import urlparse
from datetime import time, datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

import winrm

from config import Config
from dbManager import database, tablesCheck
from dbManager import init_app, Device, User, Reservation, AuditLog, Room, Timetable, Credential
app = Flask(__name__)
app.config.from_object(Config) #Fetch Config class and apply
app.debug = True
init_app(app)

scheduler = BackgroundScheduler()
auth = HTTPBasicAuth()

key = app.config['ENCRYPTION_KEY']
cipher = Fernet(key)

socketio = SocketIO(app, ssl_context='adhoc') #enable SSL, 'adhoc' self signs the certificate, DEV ONLY
AD_KEY = app.config['AD_KEY']

#Initialise extensions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

bcrypt = Bcrypt(app)

def isSafeRedirect(target):
    if not target: #Prevents user from being unintentionally redirected if no target set
        return False
    parsed_url = urlparse(target)
    return parsed_url.netloc == "" #Allow only relative urls


def lockPC(reservation):
    try:
        credential = Credential.query.filter_by(user_id=reservation.user_id).first()
        if not credential:
            flash("Credential not found", "danger")
            return
        username = credential.username
        encoded_password = credential.password #Password is still encoded from storage
        address = credential.address

        encrypted_password = base64.b64decode(encoded_password) #Base64 decode pass first
        password = (cipher.decrypt(encrypted_password)).decode("utf-8")

        #Establish WinRM session
        sessionRM = winrm.Session(f'http://{address}:5985/wsman', auth=(username, password))

        #Attempt locking
        command = 'rundll32.exe user32.dll,LockWorkStation'
        result = sessionRM.run_cmd(command)

        if result.status_code == 0:
            log_event(username, credential.hostname, "PC Locked Successfully", f"PC {credential.hostname} locked for user {username}")
        else:
            log_event(username, credential.hostname, "PC Locked Unsuccessfully", f"PC {credential.hostname} was not locked for user {username}")
    except Exception as e:
        print(e)


def check_reservations():
    with app.app_context():
        # Fetch current date and time
        now = datetime.now()
        nowPlusFive = now + timedelta(minutes=5)

        # Extract current date and time for filtering
        today = now.date()
        current_time = now.time()
        time_plus_five = nowPlusFive.time()

        # Query for reservations where they match the following query
        reservationList = Reservation.query.filter(
            Reservation.date == today,  # Match today's date
        ).all()

        if reservationList:
            # Lock PCs for all reservations found
            for reservation in reservationList:
                if reservation.start_time > current_time and reservation.start_time <= time_plus_five:
                    lockPC(reservation)
                elif reservation.end_time < current_time:
                    clear_expired_reservations(reservation)


@login_manager.user_loader
def load_user(username):
    return User.query.filter_by(username=username).first()


@app.route('/')
@login_required
def index():
    rooms = Room.query.all()
    check_reservations()
    return render_template('index.html', rooms=rooms)

#FlaskForms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    passwordConfirm = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ReserveForm(FlaskForm):
    day = SelectField('Day', choices=[
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday')
    ], validators=[DataRequired()])

    time = SelectField('Time', choices=[
        (f'{hour:02}:00', f'{hour:02}:00') for hour in range(9, 18)
    ] + [
        (f'{hour:02}:30', f'{hour:02}:30') for hour in range(9, 18)
    ], validators=[DataRequired()])

    duration = SelectField('Duration', choices=[(str(minutes), f'{minutes // 60}h {minutes % 60}min')
                        for minutes in range(30, 241, 30)], validators=[DataRequired()])
    submit = SubmitField('Reserve')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Retrieve input from login form
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate if username and password are provided
        if not username or not password:
            flash("Username and password are required!", "danger")
            return render_template('login.html')  # Stay on the login page if validation fails

        # Check if user exists
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Invalid username!", "danger")
            log_event(username, "", "Login Unsuccessful", f"User {username} attempted to log in with invalid username")
            return render_template('login.html')

        # Check if password is correct
        if not verify_password(username, password):
            flash("Incorrect password!", "danger")
            log_event(username, "", "Login Unsuccessful", f"User {username} attempted to log in with incorrect password")
            return render_template('login.html')

        # User is valid after all the above checks
        log_event(username, "", "Login Successful", f"User {username} logged in successfully")
        login_user(user)

        # Handle redirection after login
        next_page = request.args.get('next')
        # Ensure the user is redirected to a safe URL (within the site)
        if isSafeRedirect(next_page):
            return redirect(next_page)
        else:
            return redirect(url_for('index'))  # Default to index page if unsafe URL

    return render_template('login.html')

@auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password, password):
        return True
    return False


@app.route('/logout')
def logout():
    log_event(current_user.username, "", "Logout", ("User " + current_user.username + " was logged out"))
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))


#Reservation Logic
@app.route('/room/<string:current_room>')
@login_required
def room(current_room):
    # Get all devices in the specified room
    devices = Device.query.filter(Device.room_number == current_room).all()
    room_object = Room.query.filter_by(room_number=current_room).first_or_404()

    #Alert user to room's EAM status
    if room_object.eam_room:
        flash("Warning: This is an EAM lab. Your reservation may be reallocated if an EAM student requires your selected device.", "warning")
    current_room = "Room " + current_room
    return render_template('room.html', room=room_object, devices=devices, current_room=current_room)

@app.route('/reserve/<string:hostname>', methods=['POST', 'GET'])
@login_required
def reserve(hostname):
    #Retrieve designated device and the room_object so that we can see if the room is EAM or lesson ongoing
    device = Device.query.filter_by(hostname=hostname).first()
    room_object = Room.query.filter_by(room_number=device.room_number).first_or_404()

    if not device or not room_object:
        log_event(current_user.username, device.hostname, "Endpoint not found", ("User " + current_user.username + " attempted to access endpoint for device " + device.hostname))
        return "Device/Room not found", 404

    #Query timetable to see if room is reserved by a lesson
    timetable = Timetable.query.filter_by(room_number=device.room_number).all()
    # Query user reservations list to see when PC is available.
    reservations = Reservation.query.filter_by(hostname=device.hostname).all()
    #Generate time objects for open hours
    hours = [time(hour) for hour in range(9, 18)]
    form = ReserveForm()
    #Check for conflicts with existing reservations
    existing_reservation = Reservation.query.filter_by(user_id=current_user.username).first()
    if form.validate_on_submit():
        # Check if student has prior reservation, only 1 reservation allowed at a time
        if existing_reservation:
            log_event(current_user.username, device.hostname, "Reservation", ("User " + current_user.username + " attempted to reserve " + device.hostname + ", but they have an existing reservation"))
            flash("You already have an active reservation. Cancel your current reservation to make a new one.","warning")
            return redirect(url_for('room', current_room=Device.query.filter_by(hostname=hostname).first().room_number))


        #Retrieve reservation parameters from forms input
        time_selected = form.time.data #HH:MM
        day_selected = form.day.data
        duration_selected = int(form.duration.data)
        hour, minute = map(int, time_selected.split(':'))

        #Calulate date of reservation from weekday
        today = datetime.today()
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_selected_index = days_of_week.index(day_selected)
        days_ahead = day_selected_index - today.weekday()

        if days_ahead <= 0:
            days_ahead += 7 #If reservation is made for day already passed this week, attempt reserve for next week
        date_selected = (today + timedelta(days=days_ahead)).date() #Calculate date on selected day
        datetime_selected = datetime.combine(date_selected, time(hour, minute))

        #Calculate reservation end time to see if it overlaps with pre-scheduled lessons
        end_datetime = datetime_selected + timedelta(minutes=duration_selected)

        #Query timetable for lessons and reservations scheduled on desired day
        lessons_for_day = Timetable.query.filter(
            Timetable.room_number == device.room_number,
            Timetable.day_of_week == date_selected.strftime('%A')
        ).all()

        reservations_for_day = Reservation.query.filter(
            Reservation.hostname == device.hostname,
            Reservation.date == date_selected
        )
        #Check results for the room and device to ensure it is available at the requested time
        for lesson in lessons_for_day:
            if lesson.start_time < end_datetime.time() and lesson.end_time > datetime_selected.time():
                log_event(current_user.username, device.hostname, "Endpoint not found", ("User " + current_user.username + " attempted to reserve " + device.hostname + ", but it conflicted with a lesson"))
                flash("Reservation overlaps with a scheduled lesson", "warning")
                return redirect(url_for('reserve', hostname=hostname))

        # Check if overlaps with existing reservations made by other students
        for reservation in reservations_for_day:
            if reservation.start_time < end_datetime.time() and reservation.end_time > datetime_selected.time():
                if not (current_user.eam_enrolled and device.eam_assigned_student == current_user.username):
                    log_event(current_user.username, device.hostname, "Reservation", ("User " + current_user.username + " attempted to reserve " + device.hostname + ", but it conflicted with another reservation"))
                    flash("Reservation overlaps with another student's reservation", "warning")
                    return redirect(url_for('reserve', hostname=hostname))
                log_event(current_user.username, reservation.hostname, "Cancellation", ("User " + reservation.user_id +"'s reservation on " + reservation.hostname + " was cancelled due to an EAM student requiring this device"))
                database.session.delete(reservation)
                database.session.commit()


        attempt_reservation = Reservation(
            user_id=current_user.username,
            hostname=device.hostname,
            room_number=device.room_number,
            start_time=datetime_selected,
            end_time=end_datetime,
            date=date_selected
        )
        database.session.add(attempt_reservation)
        database.session.commit()

        log_event(current_user.username, device.hostname, "Reservation Success", ("User " + current_user.username + " attempted to reserve " + device.hostname + ", successfully"))
        flash('Reservation successful! Please confirm your credentials so that your workstation may be locked', 'success')
        return redirect(url_for('log_credentials'))
    else:
        log_event(current_user.username, device.hostname, "Reservation Failure", ("User " + current_user.username + " posted invalid reservation form, error as follows: " + ''.join(form.errors)))
    return render_template('reserve.html', room=room_object, hostname=hostname, timetable=timetable, hours=hours, reservations=reservations, form=form, existing_reservation=existing_reservation)

@app.route('/cancel_reservation/<string:user_id>', methods=['POST'])
def cancel_reservation(user_id):
    reservation = Reservation.query.filter_by(user_id=user_id).first_or_404()
    if reservation and reservation.user_id == current_user.username:
        database.session.delete(reservation)
        database.session.commit()
        log_event(current_user.username, reservation.hostname, "Cancellation Success", ("User " + current_user.username + " attempted to cancel reservation on " + reservation.hostname + ", successfully"))
        flash('Reservation cancelled!', 'success')
    else:
        flash('Reservation not found or insufficient permissions', 'warning')
        log_event(current_user.username, reservation.hostname, "Cancellation Failure", ("User " + current_user.username + " attempted to cancel reservation on " + reservation.hostname + ", unsuccessfully"))
    return redirect(url_for('index'))

def clear_expired_reservations(reservation):
    #Log reservation being cleared whenever func called
    log_event(reservation.user_id, reservation.hostname, "Expired Reservation", ("Reservation made by " + reservation.user_id + " on device " + reservation.hostname + " has expired"))
    database.session.delete(reservation)
    # Commit changes to the database
    database.session.commit()

@app.route('/log_credentials', methods=['POST', 'GET'])
def log_credentials():
    if request.method == 'POST':
        # Retrieve input from login form
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate if username and password are provided
        if not username or not password:
            flash('Username and password are required!', 'danger')
            return render_template('validate.html')

        # Check if user exists
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Invalid username!', 'danger')
            return render_template('validate.html')

        # Check if password is correct
        if not bcrypt.check_password_hash(user.password, password):
            flash('Incorrect password!', 'danger')
            return render_template('validate.html')

        # After validation, proceed with the reservation logic
        reservation = Reservation.query.filter_by(user_id=username).first()
        if reservation:
            hostname = reservation.hostname
        else:
            flash('Reservation not found!', 'danger')
            return render_template('validate.html')

        device = Device.query.filter_by(hostname=hostname).first()
        if device:
            address = device.address
        else:
            flash('Device not found!', 'danger')
            return render_template('validate.html')

        #Encrypt password before it is stored in the database
        encrypted_password = cipher.encrypt(password.encode()).decode('utf-8')
        # Save the connection information
        ConnectionInfo = Credential(
            username=username,
            password=encrypted_password,
            hostname=hostname,
            address=address
        )
        database.session.add(ConnectionInfo)
        database.session.commit()

        flash('Credentials validated successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('validate.html')


def log_event(user_id, device_id, action, description):
    if not user_id:
        user_id = None
    if not device_id:
        device_id = None
    new_log = AuditLog(
        user_id=user_id,
        device_id=device_id,
        action=action,
        description=description,
        timestamp=datetime.now()
    )
    database.session.add(new_log)
    database.session.commit()


if __name__ == "__main__":
    tablesCheck()
    scheduler.add_job(func=check_reservations, trigger='interval', minutes=5)
    scheduler.start()
    app.run(host='0.0.0.0', port=5000)  # This will only run if this script is executed directly
