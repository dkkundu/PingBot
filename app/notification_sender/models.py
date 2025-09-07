# app/notification_sender/models.py
from datetime import datetime
import pytz # Added import for pytz
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
    company_name = db.Column(db.String(255), nullable=False)
    
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
    company_name = db.Column(db.String(255), nullable=False)
    sender_name = db.Column(db.String(255), nullable=False)
    
    service_id = db.Column(db.Integer, db.ForeignKey("alert_service.id"), nullable=True)
    config_id = db.Column(db.Integer, db.ForeignKey("alert_config.id"), nullable=True)
    device_type_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text(length=4294967295), nullable=True) # Use LONGTEXT for large content
    category = db.Column(db.Integer, nullable=True)

    # File uploads
    photo_upload = db.Column(db.String(255), nullable=True)  # For image files
    document_upload = db.Column(db.String(255), nullable=True) # For other document types

    # Scheduling fields
    start_date = db.Column(db.Date, default=lambda: datetime.now(pytz.utc).date(), nullable=False)
    start_time = db.Column(db.Time, default=lambda: datetime.now(pytz.utc).time(), nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_interval = db.Column(db.String(50), nullable=True)  # e.g., 'daily', 'weekly', 'monthly'

    # Type field
    type = db.Column(db.String(50), nullable=True)  # e.g., "One-Time", "Recurring", "Special"

    # Relationships
    user = db.relationship("User", backref="alerts")
    service = db.relationship("AlertService", backref="samples")
    config = db.relationship("AlertConfig", backref="samples")

    def __repr__(self):
        return f"<AlertSample {self.id}>"

    @property
    def category_name(self):
        category_map = {1: "System Alert", 2: "User Alert"}
        return category_map.get(self.category, "N/A")
    
    @property
    def schedule_type(self):
        return "Recurring" if self.is_recurring else "One-Time"

class AlertLog(db.Model):
    __tablename__ = "alert_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    sample_id = db.Column(db.Integer, db.ForeignKey("alert_sample.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("alert_service.id"), nullable=True, index=True)
    config_id = db.Column(db.Integer, db.ForeignKey("alert_config.id"), nullable=True, index=True)

    # Sender and target
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    # Store names for reporting
    company_name = db.Column(db.String(255), nullable=True)
    sender_name = db.Column(db.String(255), nullable=True)

    # Audience & state
    audience = db.Column(db.String(20), nullable=False, default="all")  # "single" | "common" | "all"
    status   = db.Column(db.String(20), nullable=False, default="queued", index=True)  # "queued" | "scheduled" | "sent" | "failed" | "skipped"

    # Timing
    scheduled_for = db.Column(db.DateTime, nullable=True, index=True)
    queued_at     = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(pytz.utc), index=True)
    sent_at       = db.Column(db.DateTime, nullable=True)

    # Operational info
    retry_count   = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text, nullable=True)

    # Relationships
    sample  = db.relationship("AlertSample", backref="logs")
    service = db.relationship("AlertService", lazy="joined")
    config  = db.relationship("AlertConfig", lazy="joined")
    sender  = db.relationship("User", foreign_keys=[sender_id], lazy="joined")
    target  = db.relationship("User", foreign_keys=[target_user_id], lazy="joined")

    def __repr__(self):
        return f"<AlertLog sample={self.sample_id} status={self.status} queued_at={self.queued_at}>"

class TestCredentials(db.Model):
    __tablename__ = "test_credentials"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_code = db.Column(db.String(255), nullable=False)
    service_name = db.Column(db.String(255), nullable=False) # Denormalized for easier access
    group_name = db.Column(db.String(255), nullable=True)
    group_id = db.Column(db.String(255), nullable=True)
    auth_token = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=False) # True means test credentials are active, main config is inactive

    def __repr__(self):
        return f"<TestCredentials {self.service_name} (Active: {self.is_active})>"

    @property
    def sender_display_name(self):
        # Prioritize sender_name from the log entry itself
        if self.sender_name:
            return self.sender_name
        # Fallback to the full_name of the associated User if sender_id is present
        if self.sender:
            return self.sender.full_name
        # Default if neither is available
        return "System"

    @property
    def target_display_name(self):
        return self.target.username if self.target else ("All Users" if self.audience in ("all", "common") else "N/A")

    @property
    def is_success(self):
        return self.status == "sent"
