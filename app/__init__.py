# app/__init__.py
from flask import Flask
from .app import create_app
from .extensions import db, migrate, jwt

# Import models here so Flask-Migrate can detect them
# from .notification_sender.models import AlertService, AlertConfig, AlertSample
# def create_app():
#     app = Flask(__name__)
    
#     from .notification_sender.views.alert_views import bp as alert_bp
#     app.register_blueprint(alert_bp)
    
#     return app