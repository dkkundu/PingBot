from ..extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"  

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)  # Used for login
    role = db.Column(db.String(50), nullable=False, default="employee")  # roles: admin, employee
    telegram_chat_id = db.Column(db.String(50), nullable=True)
    # Optional details
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(250), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_pic = db.Column(db.String(250), nullable=True)  # store file path or URL
    
    password_hash = db.Column(db.String(256), nullable=False)

    # New fields for permissions
    is_superuser = db.Column(db.Boolean, default=False)   # Admin or not
    is_approved = db.Column(db.Boolean, default=False)    # Must be approved by admin
    is_rejected = db.Column(db.Boolean, default=False)
    # Password methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email} ({self.role}) | Approved={self.is_approved} | Superuser={self.is_superuser}>"





