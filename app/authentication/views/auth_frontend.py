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




# -------------------- Login --------------------
@frontend_bp.route('/login', methods=['GET', 'POST'])
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


@frontend_bp.route('/')
def dashboard():
    user_id = session.get('user_id')
    current_user = User.query.get(user_id)

    if not current_user:
        flash("You must be logged in to view this page.", "danger")
        return redirect(url_for('frontend.login'))

    # Fetch all approved users (so everyone can see total users)
    approved_users = User.query.filter_by(is_approved=True).all()

    # Optionally, fetch pending users only for admin
    pending_users = []
    if current_user.role == 'admin':
        pending_users = User.query.filter_by(is_approved=False).all()

    return render_template(
        'dashboard.html',
        current_user=current_user,
        approved_users=approved_users,
        pending_users=pending_users
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

    if not current_user:
        flash("You must be logged in to view this page.", "danger")
        return redirect(url_for('frontend.login'))

    # Fetch approved users ordered by newest id first
    approved = User.query.filter_by(is_approved=True).order_by(User.id.desc()).all()

    return render_template('approved_users.html', users=approved, current_user=current_user)



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
        return redirect(url_for('frontend.login'))

    return render_template("change_password.html", user=user, current_user=user)


# -------------------- Admin: Edit User --------------------



@frontend_bp.route('/user/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    if not current_user:
        flash("You must be logged in.", "danger")
        return redirect(url_for('frontend.login'))

    # Get the user to edit
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('frontend.approved_users'))

    if request.method == 'POST':
        # Normal users can update these fields
        user.full_name = request.form.get('full_name', user.full_name)
        user.phone = request.form.get('phone', user.phone)
        user.address = request.form.get('address', user.address)
        user.bio = request.form.get('bio', user.bio)
        user.role = request.form.get('role', user.role)

        # Only admin can update sensitive fields
        if current_user.is_superuser:
            user.email = request.form.get('email', user.email)
            user.is_superuser = request.form.get('is_superuser') == 'on'
            user.is_active = request.form.get('is_active') == 'on'
            if request.form.get('is_approved') is not None:
                user.is_approved = request.form.get('is_approved') == 'on'

        # Handle profile picture
        profile_pic = request.files.get('profile_pic')
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            upload_folder = os.path.join(os.getcwd(), "app", "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            profile_pic_path = os.path.join(upload_folder, filename)
            profile_pic.save(profile_pic_path)
            user.profile_pic = f"static/uploads/{filename}"

        # Update password if provided
        new_password = request.form.get('password')
        if new_password:
            user.set_password(new_password)

        try:
            db.session.commit()
            flash("User updated successfully!", "success")
            # Redirect to user details if admin edited a pending user
            if current_user.is_superuser and not user.is_approved:
                return redirect(url_for('frontend.user_details', user_id=user.id))
            else:
                return redirect(url_for('frontend.approved_users'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating user: {str(e)}", "danger")
            return redirect(url_for('frontend.edit_user', user_id=user.id))

    return render_template("edit_user.html", user=user, current_user=current_user)


# -------------------- Admin: User Details --------------------
@frontend_bp.route('/user/details/<int:user_id>')
def user_details(user_id):
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    if not current_user:
        flash("Please log in to view user details.", "danger")
        return redirect(url_for('frontend.login'))

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for('frontend.dashboard'))

    # Only prevent non-logged-in users (everyone else can view)
    # Remove restriction for normal users to see others
    # if not current_user.is_superuser and current_user.id != user.id:
    #     flash("Unauthorized access.", "danger")
    #     return redirect(url_for('frontend.dashboard'))

    profile = getattr(user, 'profile', None)
    if profile is None:
        profile = type('Profile', (), {})()
        profile.phone = ''
        profile.address = ''
        profile.bio = ''
        profile.profile_pic = None

    is_pending = not getattr(user, 'is_approved', False)

    return render_template(
        "user_details.html",
        user=user,
        profile=profile,
        current_user=current_user,
        is_pending=is_pending
    )




# -------------------- Admin: Delete User --------------------


@frontend_bp.route('/user/delete/<int:user_id>')
def delete_user(user_id):
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    if not current_user:
        flash("Please log in first.", "danger")
        return redirect(url_for('frontend.login'))

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('frontend.approved_users'))

    # Prevent deleting self
    if current_user.id == user.id:
        flash("You cannot delete yourself.", "warning")
        return redirect(url_for('frontend.approved_users'))

    # Normal user restrictions: cannot delete superuser
    if not current_user.is_superuser and user.is_superuser:
        flash("You cannot delete a superuser.", "danger")
        return redirect(url_for('frontend.approved_users'))

    # Delete the user
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "warning")

    # Redirect to approved users page for everyone
    return redirect(url_for('frontend.approved_users'))






# --------------------  Create User --------------------
@frontend_bp.route('/users/create', methods=['GET', 'POST'])
def create_user():
    user_id = session.get('user_id')
    current_user = User.query.get(user_id)

    if not current_user:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('frontend.dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        is_approved = bool(request.form.get('is_approved'))
        phone = request.form.get('phone')
        address = request.form.get('address')
        bio = request.form.get('bio')
        profile_pic = request.files.get('profile_pic')

        # Normal users cannot create superusers
        if current_user.is_superuser:
            is_superuser = bool(request.form.get('is_superuser'))
        else:
            is_superuser = False

        # Check if email exists
        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for('frontend.create_user'))

        # Handle profile picture upload
        profile_pic_path = None
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            upload_folder = os.path.join(os.getcwd(), "app", "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            profile_pic_path = os.path.join(upload_folder, filename)
            profile_pic.save(profile_pic_path)
            profile_pic_path = f"static/uploads/{filename}"

        # Create new user
        user = User(
            full_name=full_name,
            email=email,
            role=role,
            is_superuser=is_superuser,
            is_approved=is_approved,
            phone=phone,
            address=address,
            bio=bio,
            profile_pic=profile_pic_path
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(f"User {full_name} created successfully!", "success")
        return redirect(url_for('frontend.approved_users'))

    return render_template('create_user.html', current_user=current_user)


    

