import os
from flask import Flask, send_from_directory
from dotenv import load_dotenv
from urllib.parse import quote_plus
from .extensions import db, migrate, jwt
from .authentication.views.auth_frontend import frontend_bp
from .notification_sender.views.alert_views import alert_bp
from .logging_config import flask_logger

# Optional: Celery setup
from celery import Celery

load_dotenv()

celery_app = Celery(
    "app",
    broker=os.getenv("CELERY_BROKER_URL"),
    backend=os.getenv("CELERY_BACKEND_URL")
)

def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, '..', 'media', 'uploads')

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Database configuration with URL-encoding for password
    db_user = os.getenv("MYSQL_USER", "osman")
    db_password = quote_plus(os.getenv("MYSQL_PASSWORD", "osmanosman"))  # Encode special chars like @
    db_host = os.getenv("MYSQL_HOST", "localhost")
    db_port = os.getenv("MYSQL_PORT", "3306")
    db_name = os.getenv("MYSQL_DATABASE", "Notification_Application")

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "supersecretkey")
    app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register blueprints
    app.register_blueprint(frontend_bp)
    app.register_blueprint(alert_bp, url_prefix='/alerts')

    flask_logger.info("Flask app started successfully ✅")

    @app.route('/')
    def index():
        return {"message": "App is running!"}

    @app.route('/media/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    return app








# import os
# from flask import Flask, send_from_directory
# from dotenv import load_dotenv
# from .extensions import db, migrate, jwt
# from .authentication.views.auth_frontend import frontend_bp
# from .notification_sender.views.alert_views import alert_bp
# from .logging_config import setup_logger 
# from .logging_config import flask_logger 

# load_dotenv()

# def create_app():
#     app = Flask(__name__, template_folder='../templates')
#     app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, '..', 'media', 'uploads')

#     # Ensure the folder exists
#     os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True) 
#     app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "supersecretkey")
#     app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URI")
#     app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#     app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")
#     app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

#     # Initialize extensions
#     db.init_app(app)
#     migrate.init_app(app, db)
#     jwt.init_app(app)
#     # app.config.from_object("config.Config")
#     # Register blueprints
#     app.register_blueprint(frontend_bp)
#     app.register_blueprint(alert_bp, url_prefix='/alerts')
    
#     # app.logger = setup_logger("NotificationApp", "flask_app.log")
#     flask_logger.info("Flask app started successfully ✅")
#     # flask_logger.warning("⚠️ Flask warning example")
#     # flask_logger.error("❌ Flask error example")

#     @app.route('/')
#     def index():
#         return {"message": "App is running!"}

#     @app.route('/media/uploads/<filename>')
#     def uploaded_file(filename):
#         return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

#     return app
