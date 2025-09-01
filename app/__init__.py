import os
from flask import Flask
from dotenv import load_dotenv
from .extensions import db, migrate, jwt
from .authentication.views.auth_frontend import frontend_bp
from .notification_sender.views.alert_views import alert_bp
from .logging_config import setup_logger 
from .logging_config import flask_logger 

load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')

    # Ensure the folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True) 
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "supersecretkey")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        "DATABASE_URI", "mysql+pymysql://youruser:yourpassword@127.0.0.1:3306/Notification_Application"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    # app.config.from_object("config.Config")
    # Register blueprints
    app.register_blueprint(frontend_bp)
    app.register_blueprint(alert_bp, url_prefix='/alerts')
    
    # app.logger = setup_logger("NotificationApp", "flask_app.log")
    flask_logger.info("Flask app started successfully ✅")
    # flask_logger.warning("⚠️ Flask warning example")
    # flask_logger.error("❌ Flask error example")

    @app.route('/')
    def index():
        return {"message": "App is running!"}

    return app
