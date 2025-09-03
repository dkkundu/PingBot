from app.app import create_app
from app.extensions import db
from app.authentication.models import User

app = create_app()

with app.app_context():
    print("Starting database path update...")
    users = User.query.all()
    updated_count = 0
    for user in users:
        if user.profile_pic:
            if user.profile_pic.startswith("uploads/"):
                user.profile_pic = user.profile_pic.replace("uploads/", "media/uploads/")
                updated_count += 1
                print(f"Updated user {user.email}: new profile_pic = {user.profile_pic}")
            elif user.profile_pic.startswith("static/uploads/"):
                user.profile_pic = user.profile_pic.replace("static/uploads/", "media/uploads/")
                updated_count += 1
                print(f"Updated user {user.email}: new profile_pic = {user.profile_pic}")
    
    db.session.commit()
    print(f"Database path update complete. {updated_count} users updated.")
