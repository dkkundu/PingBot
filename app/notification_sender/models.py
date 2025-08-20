# app/notification_sender/models.py
from datetime import datetime
from ..extensions import db  # use the shared db from extensions
from ..authentication.models import User  # your user model

# DO NOT create a new db = SQLAlchemy() here

class AlertService(db.Model):
    __tablename__ = "alert_service"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<AlertService {self.name}>"


class AlertConfig(db.Model):
    __tablename__ = "alert_config"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_id = db.Column(db.Integer, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("alert_service.id"), nullable=False)
    service_name = db.Column(db.String(255), nullable=False)

    # BOT fields
    group_name = db.Column(db.String(255), nullable=True)
    group_id = db.Column(db.String(255), nullable=True)
    auth_token = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Boolean, default=True)

    # SMS fields
    api = db.Column(db.String(255), nullable=True)
    api_key = db.Column(db.String(255), nullable=True)
    senderid = db.Column(db.String(255), nullable=True)

    # Relationships
    service = db.relationship("AlertService", backref="configs")

    def __repr__(self):
        return f"<AlertConfig {self.service_name}>"


class AlertSample(db.Model):
    __tablename__ = "alert_sample"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_id = db.Column(db.Integer, nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey("alert_service.id"), nullable=True)
    config_id = db.Column(db.Integer, db.ForeignKey("alert_config.id"), nullable=True)
    device_type_id = db.Column(db.Integer, nullable=True)
    
    # Add this line:
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=True)
    single_user = db.Column(db.Boolean, default=False)
    is_common = db.Column(db.Boolean, default=True)
    category = db.Column(db.Integer, nullable=True)

    start_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_interval = db.Column(db.String(50), nullable=True)
    one_time_message = db.Column(db.Boolean, default=True)

    # Relationships
    user = db.relationship("User", backref="alerts")
    service = db.relationship("AlertService", backref="samples")
    config = db.relationship("AlertConfig", backref="samples")


    def __repr__(self):
        return f"<AlertSample {self.id}>"

    @property
    def category_name(self):
        category_map = {
            1: "System Alert",
            2: "User Alert"
        }
        return category_map.get(self.category, "N/A")
