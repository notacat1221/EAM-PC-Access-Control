from flask import Flask, url_for, request, redirect, render_template, abort, session, flash
from flask_login import LoginManager, login_user, login_required
from flask_bcrypt import Bcrypt

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from urllib.parse import urlparse
from passlib.handlers.sha2_crypt import sha256_crypt

from config import Config
from dbManager import database, tablesCheck
from dbManager import init_app, Device, User, Reservation, AuditLog
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

#Login logic
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    passwordConfirm = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Login')

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
    devices = Device.query.filter_by(room=current_room).all()
    return render_template('room.html', current_room=current_room, devices=devices)

@app.route('/reserve/<string:hostname>')
@login_required
def reserve(hostname):
    device = Device.query.filter_by(hostname=hostname).first()


    # Redirect back to the room page to update the status
    return redirect(url_for('room', current_room=device.room, device=device))



@app.after_request
def set_secure_cookie(response):
    response.set_cookie('session', secure = True, httponly=True) #Prevents clientside scripts from accessing cookie
    return response

if __name__ == "__main__":
    tablesCheck()
    app.run()  # This will only run if this script is executed directly
