from flask import Flask, url_for, request, redirect, render_template, abort, session, flash
from flask_login import LoginManager, login_user, login_required, current_user
from flask_bcrypt import Bcrypt

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired

from flask_socketio import SocketIO

from urllib.parse import urlparse
from datetime import time, datetime, timedelta

from config import Config
from dbManager import database, tablesCheck
from dbManager import init_app, Device, User, Reservation, AuditLog, Room, Timetable
app = Flask(__name__)
app.config.from_object(Config) #Fetch Config class and apply
app.debug = True
init_app(app)


socketio = SocketIO(app, ssl_context='adhoc') #enable SSL, 'adhoc' self signs the certificate, DEV ONLY


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

def main():
    print()

def lockPC():
    print()

def authUser():
    print()

@login_manager.user_loader
def load_user(username):
    return User.query.get(username)  # Adjust this if your primary key is not `username`

@app.route('/')
@login_required
def index():
    rooms = Room.query.all()
    clear_expired_reservations()
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

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        #Retrieve input from login form
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        #Check if user valid, check password hash
        if user and bcrypt.check_password_hash(user.password, password):
            log_event(username, "", "Login Successful", ("User " + username + " logged in successfully"))
            login_user(user)
            next = request.args.get('next')
            #Ensure user is redirected to 'safe' page (page within our site)
            if isSafeRedirect(next):
                return redirect(next)
            else: #Return to index page if not safe url
                return redirect(url_for('index')) #If unsafe, default to index
        else:
            log_event(username, "", "Login Unsuccessful", ("User " + username + " attempted to login unsuccessfully"))
            flash("Credentials incorrect", "warning")
    return render_template('login.html')
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
        print("Form valid")
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

        #ADD SHIT HERE

        log_event(current_user.username, device.hostname, "Reservation", ("User " + current_user.username + " attempted to reserve " + device.hostname + ", successfully"))
        flash('Reservation successful!', 'success')
        return redirect(url_for('index'))
    else:
        log_event(current_user.username, device.hostname, "Reservation", ("User " + current_user.username + " posted invalid reservation form, error as follows: " + ''.join(form.errors)))
        print("Form invalid", form.errors)
    return render_template('reserve.html', room=room_object, hostname=hostname, timetable=timetable, hours=hours, reservations=reservations, form=form, existing_reservation=existing_reservation)

@app.route('/cancel_reservation/<string:user_id>', methods=['POST'])
def cancel_reservation(user_id):
    reservation = Reservation.query.filter_by(user_id=user_id).first_or_404()
    if reservation and reservation.user_id == current_user.username:
        database.session.delete(reservation)
        database.session.commit()
        log_event(current_user.username, reservation.hostname, "Cancellation", ("User " + current_user.username + " attempted to cancel reservation on " + reservation.hostname + ", successfully"))
        flash('Reservation cancelled!', 'success')
    else:
        flash('Reservation not found or insufficient permissions', 'warning')
        log_event(current_user.username, reservation.hostname, "Cancellation", ("User " + current_user.username + " attempted to cancel reservation on " + reservation.hostname + ", unsuccessfully"))
    return redirect(url_for('index'))

def clear_expired_reservations():
    now = datetime.now()
    today = now.date()
    existing_reservation = Reservation.query.filter_by(user_id=current_user.username).first()
    # Combine date and end_time to create a datetime object for comparison
    expired_reservations = Reservation.query.filter((Reservation.date <= today) & (Reservation.end_time < now))

    # Loop through expired reservations and delete them
    for reservation in expired_reservations:
        log_event(reservation.user_id, reservation.hostname, "Expired Reservation", ("Reservation made by " + reservation.user_id + " on device " + reservation.hostname + " has expired"))
        database.session.delete(reservation)

    # Commit changes to the database
    database.session.commit()

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
    app.run()  # This will only run if this script is executed directly
