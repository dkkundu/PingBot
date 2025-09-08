from sqlalchemy.orm import joinedload

import html
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app, jsonify
from app.extensions import db
from app.notification_sender.models import AlertService, AlertConfig, AlertSample, AlertLog, TestCredentials
from app.authentication.models import User
from datetime import datetime, date, time
from app.notification_sender.tasks import send_alert_task, send_test_alert_task
import time
from app.notification_sender.telegram_bot import TelegramBot
from app.notification_sender.message_geneator import get_messages

import logging
import pytz
import os
from werkzeug.utils import secure_filename
import re

import random
from app.notification_sender.models import AlertService # Ensure this import is present

def generate_unique_service_code():
    while True:
        code = str(random.randint(100, 999)) # Generate a 3-digit code
        if not AlertService.query.filter_by(code=code).first():
            return code

alert_bp = Blueprint('alert', __name__, template_folder='../../templates/alerts')
bot = TelegramBot()
LOCAL_TZ = pytz.timezone("Asia/Dhaka")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@alert_bp.route('/logs')
def list_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    sample_id = request.args.get('sample_id', type=int)
    query = AlertLog.query.options(joinedload(AlertLog.sender)) # Explicitly load sender
    if sample_id:
        query = query.filter_by(sample_id=sample_id)
    
    logs_pagination = query.order_by(AlertLog.queued_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    logs = logs_pagination.items

    for log in logs:
        if log.queued_at:
            log.queued_at = pytz.utc.localize(log.queued_at).astimezone(LOCAL_TZ)
        if log.sent_at:
            log.sent_at = pytz.utc.localize(log.sent_at).astimezone(LOCAL_TZ)
        if log.scheduled_for:
            log.scheduled_for = pytz.utc.localize(log.scheduled_for).astimezone(LOCAL_TZ)
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    return render_template('list_logs.html', logs=logs, current_user=current_user, sample_id=sample_id, logs_pagination=logs_pagination)


@alert_bp.route('/logs/<int:id>')
def detail_log(id):
    log = AlertLog.query.options(joinedload(AlertLog.sender)).get_or_404(id)
    if log.queued_at:
        log.queued_at = pytz.utc.localize(log.queued_at).astimezone(LOCAL_TZ)
    if log.sent_at:
        log.sent_at = pytz.utc.localize(log.sent_at).astimezone(LOCAL_TZ)
    if log.scheduled_for:
        log.scheduled_for = pytz.utc.localize(log.scheduled_for).astimezone(LOCAL_TZ)
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    return render_template(
        'detail_log.html',
        log=log,
        current_user=current_user
    )


@alert_bp.route('/logs/delete/<int:id>', methods=['POST'])
def delete_log(id):
    log = AlertLog.query.get_or_404(id)
    db.session.delete(log)
    db.session.commit()
    flash('Alert Log deleted successfully!')
    return redirect(url_for('alert.list_logs'))


@alert_bp.route('/services')
def list_services():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    services_pagination = AlertService.query.paginate(page=page, per_page=per_page, error_out=False)
    services = services_pagination.items

    current_user = User.query.get(session.get('user_id'))
    return render_template('list_services.html', services=services, current_user=current_user, services_pagination=services_pagination)

@alert_bp.route('/services/create', methods=['GET', 'POST'])
def create_service():
    current_user = User.query.get(session.get('user_id'))
    if request.method == 'POST':
        name = request.form['name']
        code = request.form['code']
        description = request.form.get('description')
        service = AlertService(name=name, code=code, description=description)
        db.session.add(service)
        db.session.commit()
        flash('Alert Service created successfully!')
        return redirect(url_for('alert.list_services'))
    suggested_codes = []
    for _ in range(3): # Generate 3 unique codes
        suggested_codes.append(generate_unique_service_code())
    
    return render_template('create_service.html', current_user=current_user, suggested_codes=suggested_codes)

@alert_bp.route('/services/edit/<int:id>', methods=['GET', 'POST'])
def edit_service(id):
    service = AlertService.query.get_or_404(id)
    current_user = User.query.get(session.get('user_id'))
    if request.method == 'POST':
        name = request.form['name']
        code = request.form['code']
        description = request.form.get('description')
        service = AlertService(name=name, code=code, description=description)
        db.session.commit()
        flash('Alert Service updated successfully!')
        return redirect(url_for('alert.list_services'))
    return render_template('edit_service.html', service=service, current_user=current_user)

@alert_bp.route('/services/delete/<int:id>', methods=['POST'])
def delete_service(id):
    service = AlertService.query.get_or_404(id)
    for config in service.configs:
        AlertSample.query.filter_by(config_id=config.id).delete()
        AlertLog.query.filter_by(config_id=config.id).delete()
    AlertConfig.query.filter_by(service_id=service.id).delete()
    db.session.delete(service)
    db.session.commit()
    flash('Service and related configs & samples deleted!')
    return redirect(url_for('alert.list_services'))

@alert_bp.route('/services/<int:id>')
def detail_service(id):
    service = AlertService.query.get_or_404(id)
    current_user = User.query.get(session.get('user_id'))
    configs = AlertConfig.query.filter_by(service_id=service.id).all()
    return render_template('detail_service.html', service=service, configs=configs, current_user=current_user)


@alert_bp.route('/configs')
def list_configs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    configs_pagination = AlertConfig.query.paginate(page=page, per_page=per_page, error_out=False)
    configs = configs_pagination.items

    current_user = User.query.get(session.get('user_id'))
    return render_template('list_configs.html', configs=configs, current_user=current_user, configs_pagination=configs_pagination)
@alert_bp.route('/configs/create', methods=['GET', 'POST'])
def create_config():
    services = AlertService.query.all()
    current_user = User.query.get(session.get('user_id'))

    if request.method == 'POST':
        service_code = request.form['service_code']
        service = AlertService.query.filter_by(code=service_code).first()
        if not service:
            flash('Invalid Service Code provided.', 'error')
            return redirect(url_for('alert.create_config'))
        
        status_value = bool(int(request.form.get('status')))

        config = AlertConfig(
            company_name=request.form.get('company_name'),
            service_id=service.id,
            service_name=service.name,
            group_name=request.form.get('group_name'),
            group_id=request.form.get('group_id'),
            auth_token=request.form.get('auth_token'),
            status=status_value,
            api=request.form.get('api'),
            api_key=request.form.get('api_key'),
            senderid=request.form.get('senderid')
        )

        db.session.add(config)
        db.session.commit()
        flash('Alert Config created successfully!')
        return redirect(url_for('alert.list_configs'))

    return render_template('create_config.html', services=services, current_user=current_user)

@alert_bp.route('/configs/edit/<int:id>', methods=['GET', 'POST'])
def edit_config(id):
    config = AlertConfig.query.get_or_404(id)
    services = AlertService.query.all()
    current_user = User.query.get(session.get('user_id'))

    if request.method == 'POST':
        service_code = request.form['service_code']
        service = AlertService.query.filter_by(code=service_code).first()
        if not service:
            flash('Invalid Service Code provided.', 'error')
            return redirect(url_for('alert.edit_config', id=id))

        config.company_name = request.form.get('company_name')
        config.service_id = service.id
        config.service_name = service.name
        config.group_name = request.form.get('group_name')
        config.group_id = request.form.get('group_id')
        config.auth_token = request.form.get('auth_token')
        config.status = bool(int(request.form.get('status')))
        config.api = request.form.get('api')
        config.api_key = request.form.get('api_key')
        config.senderid = request.form.get('senderid')

        db.session.commit()
        flash('Alert Config updated successfully!')
        return redirect(url_for('alert.list_configs'))

    # Ensure config.service is available for the template
    config.service = AlertService.query.get(config.service_id)
    return render_template('edit_config.html', config=config, services=services, current_user=current_user)


@alert_bp.route('/configs/delete/<int:id>', methods=['POST'])
def delete_config(id):
    config = AlertConfig.query.get_or_404(id)
    AlertSample.query.filter_by(config_id=config.id).delete()
    AlertLog.query.filter_by(config_id=config.id).delete()
    db.session.delete(config)
    db.session.commit()
    flash('Alert Config and related logs deleted!')
    return redirect(url_for('alert.list_configs'))

@alert_bp.route('/configs/<int:id>')
def detail_config(id):
    config = AlertConfig.query.get_or_404(id)
    current_user = User.query.get(session.get('user_id'))
    return render_template('detail_config.html', config=config, current_user=current_user)

# ---------------- ALERT SAMPLES ----------------
@alert_bp.route('/samples')
def list_samples():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    samples_pagination = AlertSample.query.order_by(AlertSample.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    samples = samples_pagination.items

    current_user = User.query.get(session.get('user_id'))

    for sample in samples:
        if sample.start_date and sample.start_time:
            combined_start_datetime_utc = datetime.combine(sample.start_date, sample.start_time).replace(tzinfo=pytz.utc)
            sample.start_datetime_local = combined_start_datetime_utc.astimezone(LOCAL_TZ)
        else:
            sample.start_datetime_local = None

    return render_template('list_samples.html', samples=samples, current_user=current_user, samples_pagination=samples_pagination)


@alert_bp.route('/samples/create', methods=['GET', 'POST'])
def create_sample():
    services = AlertService.query.all()
    configs = AlertConfig.query.all()
    users = User.query.all()
    current_user = User.query.get(session.get('user_id'))

    for config_item in configs:
        config_item.service = AlertService.query.get(config_item.service_id)

    if request.method == 'POST':
        try:
            service_code = request.form['service_code']
            service = AlertService.query.filter_by(code=service_code).first()
            if not service:
                flash('Invalid Service Code provided.', 'error')
                return redirect(url_for('alert.create_sample'))

            config = AlertConfig.query.get(request.form['config_id'])
            user = User.query.get(request.form.get('user_id')) if request.form.get('user_id') else None
            
            current_user_id_for_task = current_user.id if current_user else None
            user_id_for_task = user.id if user else None

            # Handle photo and document uploads
            photo_file = request.files.get('photo_upload')
            document_file = request.files.get('document_upload')
            photo_filename = None
            document_filename = None

            logger.info(f"Photo file received: {bool(photo_file)} - Filename: {photo_file.filename if photo_file else 'N/A'}")
            logger.info(f"Document file received: {bool(document_file)} - Filename: {document_file.filename if document_file else 'N/A'}")

            if photo_file and photo_file.filename != '':
                photo_filename = secure_filename(photo_file.filename)
                logger.info(f"Saving photo: {photo_filename}")
                photo_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], photo_filename))
                logger.info(f"Photo saved: {photo_filename}")

            if document_file and document_file.filename != '':
                document_filename = secure_filename(document_file.filename)
                logger.info(f"Saving document: {document_filename}")
                document_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], document_filename))
                logger.info(f"Document saved: {document_filename}")

            start_date_str = request.form.get('start_date')
            start_time_str = request.form.get('start_time')
            end_date_str = request.form.get('end_date')

            start_datetime = None
            if start_date_str and start_time_str:
                start_datetime = datetime.strptime(f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M")
                start_datetime = LOCAL_TZ.localize(start_datetime)

            end_date = None
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            is_recurring = 'is_recurring' in request.form
            received_recurrence_interval = request.form.get('recurrence_interval')
            
            sender_name_from_form = request.form.get('sender_name')
            if sender_name_from_form:
                final_sender_name = sender_name_from_form
            elif current_user and current_user.full_name:
                final_sender_name = current_user.full_name
            else:
                final_sender_name = "System"

            new_sample = AlertSample(
                company_name=request.form.get('company_name'),
                sender_name=final_sender_name,
                service_id=service.id,
                config_id=config.id,
                user_id=user.id if user else None,
                device_type_id=int(request.form.get('device_type_id')) if request.form.get('device_type_id') else None,
                title=request.form['title'],
                body=request.form.get('body'),
                # photo_upload and document_upload will be set by the Celery task
                start_date=start_datetime.astimezone(pytz.utc).date() if start_datetime else None,
                start_time=start_datetime.astimezone(pytz.utc).time() if start_datetime else None,
                end_date=end_date,
                is_recurring=is_recurring,
                recurrence_interval=received_recurrence_interval if is_recurring else None,
                type="Recurring" if is_recurring else "One-Time"
            )
            db.session.add(new_sample)
            db.session.commit()
            db.session.refresh(new_sample)

            # Dispatch task to handle file uploads and AlertLog creation
            from app.notification_sender.tasks import process_sample_creation_task

            from app.notification_sender.tasks import process_sample_creation_task
            
            max_retries = 3
            for i in range(max_retries):
                try:
                    process_sample_creation_task.delay(
                        new_sample.id,
                        photo_filename,
                        document_filename,
                        start_datetime.astimezone(pytz.utc).isoformat() if start_datetime else None,
                        datetime.now(pytz.utc).isoformat(),
                        current_user_id_for_task,
                        user_id_for_task,
                        "all", # audience
                        service.id,
                        config.id,
                        new_sample.sender_name
                    )
                    break # If successful, break the loop
                except Exception as celery_e:
                    logger.warning(f"Attempt {i+1}/{max_retries} to dispatch Celery task failed: {celery_e}")
                    if i < max_retries - 1:
                        time.sleep(1) # Wait a bit before retrying
                    else:
                        raise # Re-raise if all retries fail
            flash('Alert Sample created successfully!', 'success')
            db.session.close() # Explicitly close the session
            return redirect(url_for('alert.list_samples'))

        except Exception as e:
            db.session.rollback()
            logger.exception("Error creating sample:")
            flash(f'An error occurred while creating the sample: {e}', 'error')
            return redirect(url_for('alert.create_sample'))

    return render_template('create_sample.html', services=services, configs=configs, users=users, current_user=current_user)


@alert_bp.route('/samples/edit/<int:id>', methods=['GET', 'POST'])
def edit_sample(id):
    sample = AlertSample.query.get_or_404(id)
    services = AlertService.query.all()
    configs = AlertConfig.query.all()
    users = User.query.all()
    current_user = User.query.get(session.get('user_id'))

    log = AlertLog.query.filter_by(sample_id=sample.id).order_by(AlertLog.queued_at.desc()).first()

    for config_item in configs:
        config_item.service = AlertService.query.get(config_item.service_id)

    if request.method == 'POST':
        service_code = request.form['service_code']
        service = AlertService.query.filter_by(code=service_code).first()
        if not service:
            flash('Invalid Service Code provided.', 'error')
            return redirect(url_for('alert.edit_sample', id=id))

        config = AlertConfig.query.get(request.form['config_id'])
        user = User.query.get(request.form.get('user_id')) if request.form.get('user_id') else None

        # Handle photo and document uploads
        photo_file = request.files.get('photo_upload')
        document_file = request.files.get('document_upload')

        logger.info(f"Edit Sample - Photo file received: {bool(photo_file)} - Filename: {photo_file.filename if photo_file else 'N/A'}")
        logger.info(f"Edit Sample - Document file received: {bool(document_file)} - Filename: {document_file.filename if document_file else 'N/A'}")

        if photo_file and photo_file.filename != '':
            photo_filename = secure_filename(photo_file.filename)
            logger.info(f"Edit Sample - Saving photo: {photo_filename}")
            photo_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], photo_filename))
            logger.info(f"Edit Sample - Photo saved: {photo_filename}")
            sample.photo_upload = photo_filename

        if document_file and document_file.filename != '':
            document_filename = secure_filename(document_file.filename)
            logger.info(f"Edit Sample - Saving document: {document_filename}")
            document_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], document_filename))
            logger.info(f"Edit Sample - Document saved: {document_filename}")
            sample.document_upload = document_filename

        sender_name_from_form = request.form.get('sender_name')
        if sender_name_from_form:
            final_sender_name = sender_name_from_form
        elif current_user and current_user.full_name:
            final_sender_name = current_user.full_name
        else:
            final_sender_name = "System"

        sample.company_name = request.form.get('company_name')
        sample.sender_name = final_sender_name,

        sample.service_id = service.id
        sample.config_id = config.id
        sample.title = request.form['title']
        sample.body = request.form.get('body')
        
        is_recurring = 'is_recurring' in request.form
        sample.is_recurring = is_recurring
        
        if sample.is_recurring:
            sample.recurrence_interval = request.form.get('recurrence_interval')
        else:
            sample.recurrence_interval = None
            
        received_recurrence_interval = request.form.get('recurrence_interval')
        logger.info(f"Received recurrence_interval from form (edit_sample): {received_recurrence_interval}")

        sample.type = "Recurring" if is_recurring else "One-Time"

        start_date_str = request.form.get('start_date')
        start_time_str = request.form.get('start_time')
        end_date_str = request.form.get('end_date')

        start_datetime = None
        if start_date_str and start_time_str:
            start_datetime = datetime.strptime(f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M")
            start_datetime = LOCAL_TZ.localize(start_datetime)

        end_date = None
        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        sample.start_date=start_datetime.astimezone(pytz.utc).date() if start_datetime else None
        sample.start_time=start_datetime.astimezone(pytz.utc).time() if start_datetime else None
        sample.end_date=end_date

        db.session.commit()

        new_log = AlertLog(
            sample_id=sample.id,
            service_id=sample.service_id,
            config_id=sample.config_id,
            sender_id=current_user.id if current_user else None,
            sender_name=sample.sender_name,
            target_user_id=user.id if user else None,
            audience="all",
            status="queued",
            scheduled_for=start_datetime.astimezone(pytz.utc) if start_datetime else None,
            queued_at=datetime.now(pytz.utc)
        )
        db.session.add(new_log)
        db.session.commit()

        

        flash('Alert Sample updated successfully!')
        return redirect(url_for('alert.list_samples'))

    if sample.start_date and sample.start_time:
        combined_start_datetime_utc = datetime.combine(sample.start_date, sample.start_time).replace(tzinfo=pytz.utc)
        local_start_datetime = combined_start_datetime_utc.astimezone(LOCAL_TZ)
        sample.start_date_str = local_start_datetime.strftime("%Y-%m-%d")
        sample.start_time_str = local_start_datetime.strftime("%H:%M")
    else:
        sample.start_date_str = ""
        sample.start_time_str = ""

    if sample.end_date:
        sample.end_date_str = sample.end_date.strftime("%Y-%m-%d")
    else:
        sample.end_date_str = ""

    sample.service = AlertService.query.get(sample.service_id)

    return render_template('edit_sample.html', sample=sample, services=services, configs=configs, users=users, current_user=current_user)


@alert_bp.route('/samples/delete/<int:id>', methods=['POST'])
def delete_sample(id):
    sample = AlertSample.query.get_or_404(id)
    
    # Delete related logs first
    AlertLog.query.filter_by(sample_id=sample.id).delete()
    
    # Delete the sample itself
    db.session.delete(sample)
    db.session.commit()
    
    flash('🗑️ Alert Sample and its logs deleted successfully!', 'success')
    return redirect(url_for('alert.list_samples'))



@alert_bp.route('/samples/<int:id>')
def detail_sample(id):
    sample = AlertSample.query.get_or_404(id)
    service = AlertService.query.get(sample.service_id)
    config = AlertConfig.query.get(sample.config_id)
    user = User.query.get(sample.user_id) if sample.user_id else None
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    start_datetime = None
    if sample.start_date and sample.start_time:
        # Combine date and time to a naive datetime
        naive_start_datetime = datetime.combine(sample.start_date, sample.start_time)
        # Localize it as UTC, then convert to LOCAL_TZ
        start_datetime = pytz.utc.localize(naive_start_datetime).astimezone(LOCAL_TZ)
    sample.start_datetime_str = start_datetime.strftime("%I:%M %p %Y-%m-%d") if start_datetime else ""

    logs = AlertLog.query.filter_by(sample_id=sample.id).order_by(AlertLog.queued_at.desc()).all()
    for log in logs:
        if log.queued_at:
            log.queued_at = pytz.utc.localize(log.queued_at).astimezone(LOCAL_TZ)
        if log.sent_at:
            log.sent_at = pytz.utc.localize(log.sent_at).astimezone(LOCAL_TZ)
        if log.scheduled_for:
            log.scheduled_for = pytz.utc.localize(log.scheduled_for).astimezone(LOCAL_TZ)
    return render_template('detail_sample.html', sample=sample, service=service, config=config, user=user, current_user=current_user, logs=logs)


# ---------------- TEST CREDENTIALS ----------------
@alert_bp.route('/test_credentials')
def list_test_credentials():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    test_credentials_pagination = TestCredentials.query.order_by(TestCredentials.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    test_credentials = test_credentials_pagination.items

    current_user = User.query.get(session.get('user_id'))
    return render_template('list_test_credentials.html', test_credentials=test_credentials, current_user=current_user, test_credentials_pagination=test_credentials_pagination)

@alert_bp.route('/test_credentials/create', methods=['GET', 'POST'])
def create_test_credential():
    services = AlertService.query.all()
    current_user = User.query.get(session.get('user_id'))

    if request.method == 'POST':
        service_code = request.form['service_code']
        service = AlertService.query.filter_by(code=service_code).first()
        if not service:
            flash('Invalid Service Code provided.', 'error')
            return redirect(url_for('alert.create_test_credential'))
        
        is_active = 'is_active' in request.form

        if is_active:
            # Deactivate all other test credentials for this service
            TestCredentials.query.filter_by(
                service_code=service.code,
                is_active=True
            ).update({TestCredentials.is_active: False})
            db.session.commit() # Commit deactivation before adding new active one

        test_credential = TestCredentials(
            service_code=service.code,
            service_name=service.name,
            group_name=request.form.get('group_name'),
            group_id=request.form.get('group_id'),
            auth_token=request.form.get('auth_token'),
            is_active=is_active
        )

        db.session.add(test_credential)
        db.session.commit()

        flash('Test Credential created successfully!', 'success')
        return redirect(url_for('alert.list_test_credentials'))

    return render_template('create_test_credential.html', services=services, current_user=current_user)

@alert_bp.route('/test_credentials/edit/<int:id>', methods=['GET', 'POST'])
def edit_test_credential(id):
    test_credential = TestCredentials.query.get_or_404(id)
    services = AlertService.query.all()
    current_user = User.query.get(session.get('user_id'))

    if request.method == 'POST':
        service_code = request.form['service_code']
        service = AlertService.query.filter_by(code=service_code).first()
        if not service:
            flash('Invalid Service provided.', 'error')
            return redirect(url_for('alert.edit_test_credential', id=id))
        
        is_active = 'is_active' in request.form

        if is_active:
            # Deactivate all other test credentials for this service, excluding the current one
            TestCredentials.query.filter(
                TestCredentials.service_code == service.code,
                TestCredentials.is_active == True,
                TestCredentials.id != test_credential.id
            ).update({TestCredentials.is_active: False})
            db.session.commit() # Commit deactivation before updating current one

        test_credential.service_code = service.code
        test_credential.service_name = service.name
        test_credential.group_name = request.form.get('group_name')
        test_credential.group_id = request.form.get('group_id')
        test_credential.auth_token = request.form.get('auth_token')
        test_credential.is_active = is_active

        db.session.commit()

        flash('Test Credential updated successfully!', 'success')
        return redirect(url_for('alert.list_test_credentials'))

    return render_template('edit_test_credential.html', test_credential=test_credential, services=services, current_user=current_user)

@alert_bp.route('/test_credentials/delete/<int:id>', methods=['POST'])
def delete_test_credential(id):
    test_credential = TestCredentials.query.get_or_404(id)
    
    # Get service_id from AlertService using service_code before deleting test_credential
    service = AlertService.query.filter_by(code=test_credential.service_code).first()
    service_id = service.id if service else None

    db.session.delete(test_credential)
    db.session.commit()

    flash('Test Credential deleted successfully!', 'success')
    return redirect(url_for('alert.list_test_credentials'))

@alert_bp.route('/samples/test_message/<int:sample_id>', methods=['POST'])
def test_sample_message(sample_id):
    sample = AlertSample.query.get_or_404(sample_id)

    try:
        # Find the active TestCredentials for this sample's service
        test_credential = TestCredentials.query.filter_by(
            service_code=sample.config.service.code,
            is_active=True
        ).first()
    except Exception as e:
        logger.exception("Error fetching TestCredentials:")
        return jsonify({"show_modal": True, "title": "Action Required", "message": f"An error occurred while fetching Test Credentials: {str(e)}", "category": "danger"})

    print(f"Testing sample ID: {sample.id} with service code: {sample.config.service.code} \n")
    print(f"test_credential: {test_credential}\n")

    if not test_credential:
        return jsonify({"show_modal": True, "title": "Action Required", "message": "No active Test Credentials found for this service.", "category": "danger"})

    send_test_alert_task.delay(sample.id, test_credential.id)
    return jsonify({"show_modal": True, "title": "Request in Process", "message": "Your test message is being processed.", "category": "success"})

