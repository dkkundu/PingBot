# app/app.py
from flask import Flask
from .extensions import db, migrate, jwt
from .authentication.urls import initialize_routes
from app.authentication.views.auth_frontend import frontend_bp

def create_app():
    app = Flask(__name__, template_folder='../templates')

    app.config['SECRET_KEY'] = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://youruser:yourpassword@127.0.0.1:3306/Notification_Application"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = "jwt-secret-key"
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    # Initialize routes
    initialize_routes(app)
    app.register_blueprint(frontend_bp)
    @app.route('/')
    def index():
        return {"message": "App is running!"}

    return app
