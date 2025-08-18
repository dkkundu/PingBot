from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app.authentication.models import User
from app.extensions import db
import os

from werkzeug.utils import secure_filename

frontend_bp = Blueprint('frontend', __name__, template_folder='../../templates/auth')

UPLOAD_FOLDER = "/static/uploads"  # Make sure this folder exists
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif','webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# -------------------- Registration --------------------

@frontend_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        bio = request.form.get('bio')
        profile_pic = request.files.get('profile_pic')

        # Check if email exists
        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for('frontend.register'))

        # Handle profile picture upload
        profile_pic_path = None
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            
            # Full filesystem path
            upload_folder = os.path.join(os.getcwd(), "app", "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)  # Create folder if it doesn't exist
            
            profile_pic_path = os.path.join(upload_folder, filename)
            profile_pic.save(profile_pic_path)
            
            # Store relative path for HTML
            profile_pic_path = f"static/uploads/{filename}"

        user = User(
            full_name=full_name,
            email=email,
            role="employee",
            is_superuser=False,
            is_approved=False,
            phone=phone,
            address=address,
            bio=bio,
            profile_pic=profile_pic_path
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("User registered successfully! Waiting for admin approval.", "success")
        return redirect(url_for('frontend.login'))

    return render_template('register.html')



# -------------------- Login --------------------
@frontend_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid credentials", "danger")
            return redirect(url_for('frontend.login'))

        if user.role != "admin" and not user.is_approved:
            flash("Your account is pending approval.", "warning")
            return redirect(url_for('frontend.login'))

        session['user_id'] = user.id
        flash("Login successful!", "success")
        return redirect(url_for('frontend.dashboard'))

    return render_template('login.html')


# -------------------- Logout --------------------
@frontend_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('frontend.login'))


# -------------------- Dashboard --------------------
# @frontend_bp.route('/dashboard')
# def dashboard():
#     user_id = session.get('user_id')
#     if not user_id:
#         flash("Please login first.", "warning")
#         return redirect(url_for('frontend.login'))

#     user = User.query.get(user_id)
#     if not user:
#         flash("User not found", "danger")
#         return redirect(url_for('frontend.login'))

#     # Admin view: show pending users
#     pending_users = User.query.filter_by(is_approved=False).all() if user.role == "admin" else None

#     return render_template('dashboard.html', current_user=user, pending_users=pending_users)


@frontend_bp.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please login first.", "warning")
        return redirect(url_for('frontend.login'))

    user = User.query.get(user_id)
    if not user:
        flash("User not found", "danger")
        return redirect(url_for('frontend.login'))

    # Only for admin
    if user.role == "admin":
        pending_users = User.query.filter_by(is_approved=False).all()
        approved_users = User.query.filter_by(is_approved=True).all()
    else:
        pending_users = None
        approved_users = None

    return render_template(
        'dashboard.html', 
        current_user=user, 
        pending_users=pending_users, 
        approved_users=approved_users
    )



# -------------------- Admin Pages --------------------
@frontend_bp.route('/users/pending')
def pending_users():
    user_id = session.get('user_id')
    current_user = User.query.get(user_id)

    if not current_user or current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('frontend.pending_users'))  

    pending = User.query.filter_by(is_approved=False).all()
    return render_template('pending_users.html', users=pending, current_user=current_user)

    # return render_template('pending_users.html', users=pending)



@frontend_bp.route('/users/approved')
def approved_users():
    user_id = session.get('user_id')
    current_user = User.query.get(user_id)
    if not current_user or current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('frontend.approved_users'))

    approved = User.query.filter_by(is_approved=True).all()
    return render_template('approved_users.html', users=approved,current_user=current_user)


@frontend_bp.route('/users/approve/<int:user_id>')
def approve_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        user.is_rejected = False
        db.session.commit()
        flash(f"{user.email} approved!", "success")
    return redirect(url_for('frontend.pending_users'))  # <-- redirect here

@frontend_bp.route('/users/reject/<int:user_id>')
def reject_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f"{user.email} rejected and removed!", "warning")
    else:
        flash("User not found!", "danger")
    return redirect(url_for('frontend.pending_users'))  # <-- redirect here


@frontend_bp.route('/profile', methods=['GET'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please login first.", "warning")
        return redirect(url_for('frontend.login'))

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('frontend.login'))

    return render_template("profile_view.html", user=user, current_user=user)


@frontend_bp.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please login first.", "warning")
        return redirect(url_for('frontend.login'))

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('frontend.login'))

    if request.method == 'POST':
        # Update fields
        user.full_name = request.form.get('full_name')
        # user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        user.bio = request.form.get('bio')

        # Handle profile picture upload
        profile_pic = request.files.get('profile_pic')
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            upload_folder = os.path.join(os.getcwd(), "app", "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            profile_pic_path = os.path.join(upload_folder, filename)
            profile_pic.save(profile_pic_path)
            user.profile_pic = f"static/uploads/{filename}"

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('frontend.profile'))

    return render_template("profile_edit.html", user=user, current_user=user)


@frontend_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please login first.", "warning")
        return redirect(url_for('frontend.login'))

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('frontend.login'))

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Check current password
        if not user.check_password(current_password):
            flash("Current password is incorrect!", "danger")
            return redirect(url_for('frontend.change_password'))

        # Check new passwords match
        if new_password != confirm_password:
            flash("New passwords do not match!", "danger")
            return redirect(url_for('frontend.change_password'))

        # Update password
        user.set_password(new_password)
        db.session.commit()
        flash("Password changed successfully!", "success")
        return redirect(url_for('frontend.profile'))

    return render_template("change_password.html", user=user, current_user=user)


# -------------------- Admin: Edit User --------------------
@frontend_bp.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    # Get current logged-in user
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    # Only allow admin/superuser
    if not current_user or not current_user.is_superuser:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('frontend.approved_users'))

    # Get the user to edit
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('frontend.approved_users'))

    if request.method == 'POST':
        # Update basic fields
        user.full_name = request.form.get('full_name', user.full_name)
        user.phone = request.form.get('phone', user.phone)
        user.address = request.form.get('address', user.address)
        user.bio = request.form.get('bio', user.bio)
        user.role = request.form.get('role', user.role)
        user.email = request.form.get('email', user.email)

        # Optional checkboxes
        user.is_superuser = request.form.get('is_superuser') == 'on'
        # Only update is_approved if checkbox exists
        if request.form.get('is_approved') is not None:
            user.is_approved = request.form.get('is_approved') == 'on'

        # Handle profile picture upload
        profile_pic = request.files.get('profile_pic')
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            upload_folder = os.path.join(os.getcwd(), "app", "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            profile_pic_path = os.path.join(upload_folder, filename)
            profile_pic.save(profile_pic_path)
            user.profile_pic = f"static/uploads/{filename}"

        # Optional: update password if provided
        new_password = request.form.get('password')
        if new_password:
            user.set_password(new_password)

        try:
            db.session.commit()
            flash("User updated successfully!", "success")
            return redirect(url_for('frontend.approved_users'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating user: {str(e)}", "danger")
            return redirect(url_for('frontend.edit_user', user_id=user.id))

    return render_template("edit_user.html", user=user, current_user=current_user)

# -------------------- Admin: User Details --------------------
@frontend_bp.route('/admin/user/details/<int:user_id>')
def user_details(user_id):
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    # Check if user is logged in and is admin
    if not current_user or not current_user.is_superuser:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('frontend.user_details'))

    # Get the user details
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('frontend.user_details'))

    # Optional: ensure profile exists
    profile = getattr(user, 'profile', None)
    if profile is None:
        profile = type('Profile', (), {})()  # create empty object to avoid attribute errors
        profile.phone = ''
        profile.address = ''
        profile.bio = ''
        profile.profile_pic = None

    return render_template(
        "user_details.html",
        user=user,        # pass the actual User object
        profile=profile,  # pass profile separately
        current_user=current_user
    )


# -------------------- Admin: Delete User --------------------
@frontend_bp.route('/admin/user/delete/<int:user_id>')
def delete_user(user_id):
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    if not current_user or not current_user.is_superuser:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('frontend.dashboard'))

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('frontend.dashboard'))

    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "warning")
    return redirect(url_for('frontend.approved_users'))
