# This file contains an example Flask-User application.
# To keep the example simple, we are applying some unusual techniques:
# - Placing everything in one file
# - Using class-based configuration (instead of file-based configuration)
# - Using string-based templates (instead of file-based templates)

from flask import Flask, render_template_string, request, Response, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_user import login_required, UserManager, UserMixin
import jsonpickle
import numpy as np
import cv2
import os
from datetime import datetime
from pathlib import Path

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///quickstart_app.sqlite'    # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False    # Avoids SQLAlchemy warning

    # Flask-User settings
    USER_APP_NAME = "Flask-User QuickStart App"      # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = False      # Disable email authentication
    USER_ENABLE_USERNAME = True    # Enable username authentication
    USER_REQUIRE_RETYPE_PASSWORD = False    # Simplify register form
    UPLOAD_FOLDER = '\\example_apps\\captures'
    # ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

def create_app():
    """ Flask application factory """
    
    # Create Flask app load app.config
    app = Flask(__name__)
    app.config.from_object(__name__+'.ConfigClass')

    # Initialize Flask-SQLAlchemy
    db = SQLAlchemy(app)

    # Define the User data-model.
    # NB: Make sure to add flask_user UserMixin !!!
    class User(db.Model, UserMixin):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')

        # User authentication information. The collation='NOCASE' is required
        # to search case insensitively when USER_IFIND_MODE is 'nocase_collation'.
        username = db.Column(db.String(100, collation='NOCASE'), nullable=False, unique=True)
        password = db.Column(db.String(255), nullable=False, server_default='')
        email_confirmed_at = db.Column(db.DateTime())

        # User information
        first_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
        last_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
        
    class Capture(db.Model):
        __tablename__ = 'captures'
        id = db.Column(db.Integer, primary_key=True)
        filename = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
        

    # Create all database tables
    db.create_all()

    # Setup Flask-User and specify the User data-model
    user_manager = UserManager(app, db, User)

    # The Home page is accessible to anyone
    @app.route('/')
    def home_page():
        # String-based templates
        return render_template_string("""
            {% extends "flask_user_layout.html" %}
            {% block content %}
                <h2>Home page</h2>
                <p><a href={{ url_for('user.register') }}>Register</a></p>
                <p><a href={{ url_for('user.login') }}>Sign in</a></p>
                <p><a href={{ url_for('home_page') }}>Home page</a> (accessible to anyone)</p>
                <p><a href={{ url_for('member_page') }}>Member page</a> (login required)</p>
                <p><a href={{ url_for('user.logout') }}>Sign out</a></p>
            {% endblock %}
            """)

    # The Members page is only accessible to authenticated users via the @login_required decorator
    @app.route('/members')
    @login_required    # User must be authenticated
    def member_page():
        # String-based templates
        return render_template_string("""
            {% extends "flask_user_layout.html" %}
            {% block content %}
                <h2>Members page</h2>
                <p><a href={{ url_for('user.register') }}>Register</a></p>
                <p><a href={{ url_for('user.login') }}>Sign in</a></p>
                <p><a href={{ url_for('home_page') }}>Home page</a> (accessible to anyone)</p>
                <p><a href={{ url_for('captures_page') }}>Captures page</a> (login required)</p>
                <p><a href={{ url_for('user.logout') }}>Sign out</a></p>
            {% endblock %}
            """)
        
    # route http posts to this method
    @app.route('/api/test', methods=['POST'])
    def test():
        r = request
        # convert string of image data to uint8
        nparr = np.fromstring(r.data, np.uint8)
        # decode image
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # do some fancy processing here....
        os.chdir(str(Path().absolute())+app.config['UPLOAD_FOLDER'])
        now = datetime.now()
        current_time = now.strftime("%H-%M-%S %d-%m-%Y") 
        filename = current_time+".jpg"
        if not cv2.imwrite(filename, img):
            raise Exception

        new_capture = Capture(filename=filename)
        db.session.add(new_capture)
        db.session.commit()
        # build a response dict to send back to client
        response = {'message': 'image received. size={}x{}'.format(img.shape[1], img.shape[0])}
        
        # encode response using jsonpickle
        response_pickled = jsonpickle.encode(response)

        return Response(response=response_pickled, status=200, mimetype="application/json")
    
    # route http posts to this method
    @app.route('/api/ping', methods=['POST'])
    def ping():
        # build a response dict to send back to client
        response = {'message': 'currently online'}
        
        # encode response using jsonpickle
        response_pickled = jsonpickle.encode(response)
        
        return Response(response=response_pickled, status=200, mimetype="application/json")

    @app.route('/display/<filename>')
    def display_image(filename):
        #print('display_image filename: ' + filename)
        return redirect(url_for('static', filename='captures/' + filename), code=301)
    
    # The Members page is only accessible to authenticated users via the @login_required decorator
    @app.route('/captures')
    @login_required    # User must be authenticated
    def captures_page():
        captures = Capture.query.all()
        # String-based templates
        return render_template_string("""
            {% for capture in captures %}
		        <img src="{{ url_for('display_image', filename=capture.filename) }}">
            {% endfor %}
            """, captures=captures)
        
    return app



# Start development web server
if __name__=='__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

