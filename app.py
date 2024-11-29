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
    return render_template('index.html')

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

    time = SelectField('Time', choices=[(f'{hour}:00', f'{hour}:00') for hour in range(9, 18)] +
                        [(f'{hour}:30', f'{hour}:30') for hour in range(9, 18)], validators=[DataRequired()])
    duration = SelectField('Duration', choices=[(str(minutes), f'{minutes // 60}h {minutes % 60}min')
                        for minutes in range(30, 241, 30)], validators=[DataRequired()])
    submit = SubmitField('Reserve')


@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            print("correct creds")
            login_user(user)
            print(login_user(user, remember=True))
            next = request.args.get('next')
            if isSafeRedirect(next):
                return redirect(next)
            else: #Return to index page if not safe url
                return redirect(url_for('index'))
        else:
            flash("Credentials incorrect")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()  # Assuming you have a RegisterForm for registration
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, usertype='student',password=hashed_password, has_reservation=False)
        database.session.add(new_user)
        database.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

#Reservation Logic
@app.route('/room/<string:current_room>')
@login_required
def room(current_room):
    # Get all devices in the specified room
    devices = Device.query.filter(Device.room_number == current_room).all()
    room_object = Room.query.filter_by(room_number=current_room).first_or_404()
    return render_template('room.html', room=room_object, devices=devices)

@app.route('/reserve/<string:hostname>', methods=['POST', 'GET'])
@login_required
def reserve(hostname):
    #Retrieve designated device and the room_object so that we can see if the room is EAM or lesson ongoing
    device = Device.query.filter_by(hostname=hostname).first()
    room_object = Room.query.filter_by(room_number=device.room_number).first_or_404()

    if not device or not room_object:
        return "Device/Room not found", 404

    #Query timetable to see if room is reserved by a lesson
    timetable = Timetable.query.filter_by(room_number=device.room_number).all()
    # Query user reservations list to see when PC is available.
    reservations = Reservation.query.filter_by(hostname=device.hostname).all()
    #Generate time objects for open hours
    hours = [time(hour) for hour in range(9, 18)]
    form = ReserveForm()
    if form.validate_on_submit():
        print(f"Form Data: {form.data}")
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
        date_selected = today + timedelta(days=days_ahead) #Calculate date on selected day
        datetime_selected = datetime.combine(date_selected, time(hour, minute))

        #Calculate reservation end time to see if it overlaps
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
                flash("Reservation overlaps with a scheduled lesson", "warning")
                return redirect(url_for('reserve', hostname=hostname))
        for reservation in reservations_for_day:
            if reservation.start_time < end_datetime and reservation.end_time > datetime_selected:
                flash("Reservation overlaps with another student's reservation", "warning")


        attempt_reservation = Reservation(
            user_id=current_user.username,
            hostname=device.hostname,
            room_number=device.room_number,
            start_time=datetime_selected,
            end_time=end_datetime,
            date=date_selected.date()
        )
        database.session.add(attempt_reservation)
        database.session.commit()

        flash('Reservation successful!', 'success')
        return redirect(url_for('room', current_room=device.room_number))
    else:
        print("Form invalid", form.errors)
    return render_template('reserve.html', room=room_object, hostname=hostname, timetable=timetable, hours=hours, reservations=reservations, form=form)



if __name__ == "__main__":
    tablesCheck()
    app.run()  # This will only run if this script is executed directly
