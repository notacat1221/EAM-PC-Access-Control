from flask import Flask, url_for, request, redirect, render_template, abort, session, flash
from flask_login import LoginManager, login_user

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from urllib.parse import urlparse
from passlib.handlers.sha2_crypt import sha256_crypt

from config import Config
from dbManager import init_app, Device, User, Reservation, AuditLog
app = Flask(__name__)
init_app(app)

socketio = SocketIO(app, ssl_context='adhoc') #enable SSL, 'adhoc' self signs the certificate, DEV ONLY

app.config.from_object(Config) #Fetch Config class and apply
#Initialise extensions
login_manager = LoginManager()
login_manager.init_app(app)
database = SQLAlchemy(app)

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
@app.route('/')
def index():
    pcs = Device.query.all()
    return render_template('index.html', pcs=pcs)
@app.route('/reserve/<string:hostname>')
def reserve(hostname):
    device = Device.query.filter_by(hostname=hostname).first()
    if device and not device.has_reservation:
        device.has_reservation = True
        database.session.commit() #IMPLEMENT AUDIT LOGGING
    return redirect(url_for('index'))
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
