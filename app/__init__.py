from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://youruser:yourpassword@127.0.0.1:3306/Notification_Application"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    Migrate(app, db)

    from .models import User
    from .urls import initialize_routes
    initialize_routes(app)

    @app.route('/')
    def index():
        return {"message": "Notification Application is running!"}

    return app
