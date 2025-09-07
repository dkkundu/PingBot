import os
from flask import Flask, send_from_directory
from dotenv import load_dotenv
from urllib.parse import quote_plus
from .extensions import db, migrate, jwt
from .authentication.views.auth_frontend import frontend_bp
from .notification_sender.views.alert_views import alert_bp
from .logging_config import flask_logger
from .celery_config import celery as celery_app
import click
from app.authentication.models import User

def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, '..', 'media', 'uploads')

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Database configuration with URL-encoding for password
    db_user = os.getenv("MYSQL_USER")
    db_password = quote_plus(os.getenv("MYSQL_PASSWORD"))  # Encode special chars like @
    db_host = os.getenv("MYSQL_HOST")
    db_port = os.getenv("MYSQL_PORT")
    db_name = os.getenv("MYSQL_DATABASE")



    print(db_port, "db_port---------------------------------")



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

    # Update celery config with app context
    celery_app.conf.update(app.config)

    flask_logger.info("Flask app started successfully ✅")

    @app.route('/')
    def index():
        return {"message": "App is running!"}

    @app.route('/media/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Custom CLI command to create an admin user
    @app.cli.command("create-admin")
    @click.argument("email")
    @click.argument("password")
    @click.argument("full_name")
    def create_admin(email, password, full_name):
        """Create an admin user with the provided email, password, and full name."""
        from app.authentication.models import User
        from app.extensions import db

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            print(f"Error: User with email {email} already exists.")
            return

        # Create new admin user
        new_user = User(
            full_name=full_name,
            email=email,
            role="admin",
            is_superuser=True,
            is_approved=True
        )
        new_user.set_password(password)

        # Add and commit to the database
        db.session.add(new_user)
        db.session.commit()
        print(f"Admin user {full_name} ({email}) created successfully!")

    return app