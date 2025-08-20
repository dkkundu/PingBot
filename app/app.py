# app/app.py
from flask import Flask
from .extensions import db, migrate, jwt
from .authentication.views.auth_frontend import frontend_bp
from .notification_sender.views.alert_views import alert_bp
# from flask_login import LoginManager
# from app.authentication.models import User 

# login_manager = LoginManager()




def create_app():
    app = Flask(__name__, template_folder='../templates')
    

    app.config['SECRET_KEY'] = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://youruser:yourpassword@127.0.0.1:3306/Notification_Application"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = "jwt-secret-key"
    
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    #ogin_manager = LoginManager()
    # login_manager.init_app(app)
    # login_manager.login_view = 'login' l 
    
    app.register_blueprint(frontend_bp)
    app.register_blueprint(alert_bp, url_prefix='/alerts')
    
    
    
    # login_manager = LoginManager()
    # login_manager.login_view = 'frontend.login'  # <-- set your correct login endpoint
    # login_manager.login_message_category = "warning"  # optional: for flash message styling
    # login_manager.login_message = "Please log in to access this page."  # optional custom message
    # login_manager.init_app(app)  # Redirect non-logged-in users to this view

    # @login_manager.user_loader
    # def load_user(user_id):
    #     return User.query.get(int(user_id))

    
    @app.route('/')
    def index():
        return {"message": "App is running!"}

    return app
