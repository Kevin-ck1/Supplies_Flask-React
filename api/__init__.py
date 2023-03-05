from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate 
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from datetime import timedelta
from sqlalchemy import MetaData
from flask_mail import Mail
from flask_cors import CORS

# Setting up custom meta data and naming convenction for the database
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)


#Setting up a database object
db = SQLAlchemy(metadata=metadata)

#Setting up a Marshmallow object
ma = Marshmallow()

#Setting up decryption algorithm
decrypt = Bcrypt()

#Setting up login manager
login_manager = LoginManager()

#Setting up JWT Manager
jwt_manager = JWTManager()

#Setting up Mail
mail = Mail()

# setting up CORS
cors = CORS()


def create_app():
    # Initialiazing the app
    app = Flask(__name__, static_folder='../front_end/build', static_url_path='')

    #Settting up the base directory - this allows us to locate the path to the database
    import os #To set out file paths
    basedir = os.path.abspath(os.path.dirname(__file__))

    #Confirg settings for the database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False # This is optional
    #Setting up secret key for the use of sessions
    SECRET_KEY = os.urandom(32)
    app.config['SECRET_KEY'] = SECRET_KEY

    # To change exp time of the tokens
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=86400)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)


    #Confirg setting for the mail 587
    app.config['MAIL_SERVER']='smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    # app.config['MAIL_SERVER']='localhost'
    # app.config['MAIL_PORT'] = 1025
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = True
    # app.config['MAIL_DEBUG'] = True
    app.config['MAIL_USERNAME'] = 'myMail@gmail.com'
    app.config['MAIL_PASSWORD'] = 'appPassword'

    app.config['MAIL_DEFAULT_SENDER'] = 'myMail@gmail.com'
    app.config['MAIL_MAX_EMAILS'] = None
    # app.config['MAIL_SUPPRESS_SEND'] = False
    app.config['MAIL_ASCII_ATTACHMENTS'] = False
    
    #Initialiaze Mail
    mail.init_app(app)

    #Initialiaze a database + Marshmellow 
    db.init_app(app)
    ma.init_app(app)
    #Creating a migration instance
    migrate = Migrate(app, db, render_as_batch=True)

    #Initialiazing decryption algorithm
    decrypt.init_app(app)

    #Initialiazing the login manager
    login_manager.init_app(app)
    
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'info'

    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    #Initialiazing the jwt manager
    jwt_manager.init_app(app)

    #Setting up the blueprints
    from .views import main #Importing the blue  prints
    app.register_blueprint(main, url_prefix="")

    #Initializing cors
    cors.init_app(app)

    #In this case to create the database we call it at the last instance
    #from .models import Movie, Person #Importing the models to the project - Note that it should be called after the db instance
    
    with app.app_context():
        db.create_all()

    return app