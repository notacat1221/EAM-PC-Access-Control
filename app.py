from flask import Flask, url_for, request, redirect, render_template, abort, session, flash
from flask_login import LoginManager, login_user

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy, DateTime

from werkzeug import url_parse
from passlib.handlers.sha2_crypt import sha256_crypt

from config import Config
app = Flask(__name__)
socketio = SocketIO(app, ssl_context='adhoc') #enable SSL, 'adhoc' self signs the certificate, DEV ONLY

app.config.from_object(Config) #Fetch Config class and apply
#Initialise extensions
login_manager = LoginManager()
login_manager.init_app(app)
database = SQLAlchemy(app)

class User(database.Model):
    username = database.Column(database.String(20), unique=True, nullable=False, primary_key=True)
    usertype = database.Column(database.String(20), nullable=False)
    has_reservation = database.Column(database.Boolean, nullable=False)

class Device(database.Model):
    hostname = database.Column(database.String(20), unique=True, nullable=False, primary_key=True)
    address = database.Column(database.String(15), nullable=False)
    room = database.Column(database.String(4), nullable=False)
    is_reserved = database.Column(database.Boolean, nullable=False)

class Reservation(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    reserved_user = database.Column(database.String(20), nullable=False)
    reserved_device = database.Column(database.String(20), nullable=False)
    reserved_time = database.Column(DateTime(timezone=True), nullable=False)

class AuditLog(database.Model):
    user_id = database.Column(database.String(20), database.ForeignKey('users.username'), primary_key=True)
    device_id = database.Column(database.String(20), database.ForeignKey('devices.hostname'), primary_key=True)
    caution_level = database.Column(database.String(20), nullable=False)

def isSafeRedirect(target):
    if not target: #Prevents user from being unintentionally redirected if no target set
        return False
    parsed_url = url_parse(target)
    return parsed_url.netloc == "" #Allow only relative urls

def main():
    print()

def lockPC():
    print()

def authUser():
    print()
@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and sha256_crypt.verify(password, user.password):
            login_user(user)
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

@app.after_request
def set_secure_cookie(response):
    response.set_cookie('session', secure = True, httponly=True) #Prevents clientside scripts from accessing cookie
    return response

if __name__ == "__main__":
    main()  # This will only run if this script is executed directly
