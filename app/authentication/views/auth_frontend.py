from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from datetime import datetime
import pytz # Added import for pytz
from sqlalchemy import func
from app.authentication.models import User
from app.extensions import db
import os
from werkzeug.utils import secure_filename
from app.notification_sender.models import AlertConfig, AlertLog,AlertSample,AlertService
from app.notification_sender.views.alert_views import LOCAL_TZ # Import LOCAL_TZ
import logging

frontend_bp = Blueprint('frontend', __name__, template_folder='../../templates/auth')

# Set up a logger for this blueprint
log = logging.getLogger(__name__)

from flask import current_app

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']




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
    log.info("Dashboard route started.")
    start_time = datetime.now()

    user_id = session.get('user_id')
    current_user = None
    if user_id:
        current_user = User.query.get(user_id)

    if not current_user:
        flash("You must be logged in to view this page.", "danger")
        return redirect(url_for('frontend.login'))

    approved_users = User.query.filter_by(is_approved=True).all()

    pending_users = []
    if current_user.role == 'admin':
        pending_users = User.query.filter_by(is_approved=False).all()

    today = datetime.now(LOCAL_TZ).date() # Get today's date in local timezone

    # Define today's start and end in local timezone
    local_today_start = LOCAL_TZ.localize(datetime.combine(today, datetime.min.time()))
    local_today_end = LOCAL_TZ.localize(datetime.combine(today, datetime.max.time()))

    # Convert to UTC for database query
    utc_today_start = local_today_start.astimezone(pytz.utc)
    utc_today_end = local_today_end.astimezone(pytz.utc)

    # Optimized query for status counts
    status_counts = db.session.query(
        func.count(AlertLog.id).label("total"),
        func.count(func.nullif(AlertLog.status != 'sent', True)).label("sent"),
        func.count(func.nullif(AlertLog.status != 'failed', True)).label("failed"),
        func.count(func.nullif(AlertLog.status.notin_(['queued', 'scheduled']), True)).label("waiting")
    ).filter(
        AlertLog.scheduled_for >= utc_today_start,
        AlertLog.scheduled_for <= utc_today_end
    ).first()

    total_scheduled_messages_today = status_counts.total
    sent_messages_today = status_counts.sent
    failed_messages_today = status_counts.failed
    waiting_messages_today = status_counts.waiting
    total_messages_for_pie_chart = sent_messages_today + failed_messages_today + waiting_messages_today

    # Get the count of group names for each service
    service_group_counts = db.session.query(
        AlertConfig.service_name,
        func.count(AlertConfig.group_name)
    ).filter(AlertConfig.group_name.isnot(None)).group_by(AlertConfig.service_name).all()

    # Optimized query for hourly message counts (MySQL-compatible)
    converted_time = func.CONVERT_TZ(AlertLog.scheduled_for, 'UTC', LOCAL_TZ.zone)
    hour_extract_func = func.extract('hour', converted_time)
    
    hourly_counts = db.session.query(
        hour_extract_func.label('hour'),
        func.count(AlertLog.id).label('total'),
        func.count(func.nullif(AlertLog.status != 'sent', True)).label('sent')
    ).filter(
        AlertLog.scheduled_for >= utc_today_start,
        AlertLog.scheduled_for <= utc_today_end
    ).group_by(hour_extract_func).all()

    # Initialize hourly data and populate with query results
    hourly_data = {i: {'total': 0, 'sent': 0} for i in range(24)}
    for row in hourly_counts:
        if row.hour is not None:
            hour = int(row.hour)
            if 0 <= hour < 24:
                hourly_data[hour]['total'] = row.total
                hourly_data[hour]['sent'] = row.sent

    # Convert hourly_data to a list of values for Chart.js
    chart_labels = []
    for i in range(24):
        if i == 0:
            chart_labels.append('12 AM')
        elif i == 12:
            chart_labels.append('12 PM')
        elif i < 12:
            chart_labels.append(f'{i} AM')
        else:
            chart_labels.append(f'{i - 12} PM')
    chart_total_data = [hourly_data[i]['total'] for i in range(24)]
    chart_sent_data = [hourly_data[i]['sent'] for i in range(24)]

    end_time = datetime.now()
    log.info(f"Dashboard route finished. Total time: {end_time - start_time}")

    return render_template(
        'dashboard.html',
        current_user=current_user,
        approved_users=approved_users,
        pending_users=pending_users,
        sent_messages_today=sent_messages_today,
        total_scheduled_messages_today=total_scheduled_messages_today,
        service_group_counts=service_group_counts,
        chart_labels=chart_labels,
        chart_total_data=chart_total_data,
        chart_sent_data=chart_sent_data,
        failed_messages_today=failed_messages_today,
        waiting_messages_today=waiting_messages_today,
        total_messages_for_pie_chart=total_messages_for_pie_chart
    )


# -------------------- Admin Pages --------------------
@frontend_bp.route('/users/pending')
def pending_users():
    user_id = session.get('user_id')
    current_user = User.query.get(user_id)

    if not current_user or current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for('frontend.pending_users'))  

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    pending_users_pagination = User.query.filter_by(is_approved=False).order_by(User.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    pending_users = pending_users_pagination.items

    start_index = (page - 1) * per_page

    return render_template('pending_users.html', users=pending_users, current_user=current_user, pending_users_pagination=pending_users_pagination, start_index=start_index)


@frontend_bp.route('/users/approved')
def approved_users():
    user_id = session.get('user_id')
    current_user = User.query.get(user_id)

    if not current_user:
        flash("You must be logged in to view this page.", "danger")
        return redirect(url_for('frontend.login'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    approved_users_pagination = User.query.filter_by(is_approved=True).order_by(User.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    approved_users = approved_users_pagination.items

    start_index = (page - 1) * per_page

    return render_template('approved_users.html', users=approved_users, current_user=current_user, approved_users_pagination=approved_users_pagination, start_index=start_index)

@frontend_bp.route('/users/approve/<int:user_id>')
def approve_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        user.is_rejected = False
        db.session.commit()
        flash(f"{user.email} approved!", "success")
    return redirect(url_for('frontend.pending_users'))


@frontend_bp.route('/users/reject/<int:user_id>')
def reject_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f"{user.email} rejected and removed!", "warning")
    else:
        flash("User not found!", "danger")
    return redirect(url_for('frontend.pending_users'))


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
        user.full_name = request.form.get('full_name')
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        user.bio = request.form.get('bio')

        profile_pic = request.files.get('profile_pic')
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            profile_pic_path = os.path.join(upload_folder, filename)
            profile_pic.save(profile_pic_path)
            user.profile_pic = f"media/uploads/{filename}"

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

        if not user.check_password(current_password):
            flash("Current password is incorrect!", "danger")
            return redirect(url_for('frontend.change_password'))

        if new_password != confirm_password:
            flash("New passwords do not match!", "danger")
            return redirect(url_for('frontend.change_password'))

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

    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('frontend.approved_users'))

    if request.method == 'POST':
        user.full_name = request.form.get('full_name', user.full_name)
        user.phone = request.form.get('phone', user.phone)
        user.address = request.form.get('address', user.address)
        user.bio = request.form.get('bio', user.bio)
        user.role = request.form.get('role', user.role)

        if current_user.is_superuser:
            user.email = request.form.get('email', user.email)
            user.is_superuser = request.form.get('is_superuser') == 'on'
            user.is_active = request.form.get('is_active') == 'on'
            if request.form.get('is_approved') is not None:
                user.is_approved = request.form.get('is_approved') == 'on'

        profile_pic = request.files.get('profile_pic')
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            profile_pic_path = os.path.join(upload_folder, filename)
            profile_pic.save(profile_pic_path)
            user.profile_pic = f"media/uploads/{filename}"

        new_password = request.form.get('password')
        if new_password:
            user.set_password(new_password)

        try:
            db.session.commit()
            flash("User updated successfully!", "success")
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

    if current_user.id == user.id:
        flash("You cannot delete yourself.", "warning")
        return redirect(url_for('frontend.approved_users'))

    if not current_user.is_superuser and user.is_superuser:
        flash("You cannot delete a superuser.", "danger")
        return redirect(url_for('frontend.approved_users'))

    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "warning")

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

        if current_user.is_superuser:
            is_superuser = bool(request.form.get('is_superuser'))
        else:
            is_superuser = False

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for('frontend.create_user'))

        profile_pic_path = None
        if profile_pic and allowed_file(profile_pic.filename):
            filename = secure_filename(profile_pic.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            profile_pic_path = os.path.join(upload_folder, filename)
            profile_pic.save(profile_pic_path)
            profile_pic_path = f"media/uploads/{filename}"

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
