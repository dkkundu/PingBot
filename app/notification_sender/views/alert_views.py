
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from app.extensions import db
from app.notification_sender.models import AlertService, AlertConfig, AlertSample
from app.authentication.models import User
import os
# from flask_login import login_required

# alert_bp = Blueprint('alert', __name__, template_folder='../../templates/')
# alert_bp = Blueprint('alert', __name__, template_folder='../templates/alerts/')
alert_bp = Blueprint('alert', __name__, template_folder='../../templates/alerts')



# ---------------- ALERT SERVICE ----------------
@alert_bp.route('/services')

def list_services():
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    services = AlertService.query.all()
    return render_template('list_services.html', services=services,current_user=current_user)

@alert_bp.route('/services/create', methods=['GET', 'POST'])
def create_service():
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    if request.method == 'POST':
        name = request.form['name']
        code = request.form['code']
        description = request.form.get('description')
        new_service = AlertService(name=name, code=code, description=description)
        db.session.add(new_service)
        db.session.commit()
        flash('Alert Service created successfully!')
        return redirect(url_for('alert.list_services'))
    return render_template('create_service.html',current_user=current_user)

@alert_bp.route('/services/edit/<int:id>', methods=['GET', 'POST'])
def edit_service(id):
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    service = AlertService.query.get_or_404(id)
    if request.method == 'POST':
        service.name = request.form['name']
        service.code = request.form['code']
        service.description = request.form.get('description')
        db.session.commit()
        flash('Alert Service updated successfully!')
        return redirect(url_for('alert.list_services'))
    return render_template('edit_service.html', service=service,current_user=current_user)

@alert_bp.route('/services/delete/<int:id>', methods=['POST'])
def delete_service(id):
    service = AlertService.query.get_or_404(id)
    
    # Delete all related samples first
    for config in service.configs:
        AlertSample.query.filter_by(config_id=config.id).delete()
    
    # Delete related configs
    AlertConfig.query.filter_by(service_id=service.id).delete()
    
    # Now delete the service
    db.session.delete(service)
    db.session.commit()
    flash('Alert Service and all related configs and samples deleted successfully!')
    return redirect(url_for('alert.list_services'))





# ---------------- ALERT CONFIG ----------------
@alert_bp.route('/configs')
def list_configs():
    configs = AlertConfig.query.all()
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    return render_template('list_configs.html', configs=configs,current_user=current_user)

@alert_bp.route('/configs/create', methods=['GET', 'POST'])
def create_config():
    services = AlertService.query.all()
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    if request.method == 'POST':
        service_id = request.form['service_id']
        service = AlertService.query.get(service_id)
        new_config = AlertConfig(
            company_id=request.form['company_id'],
            service_id=service.id,
            service_name=service.name,
            group_name=request.form.get('group_name'),
            group_id=request.form.get('group_id'),
            auth_token=request.form.get('auth_token'),
            status=bool(request.form.get('status')),
            api=request.form.get('api'),
            api_key=request.form.get('api_key'),
            senderid=request.form.get('senderid')
        )
        db.session.add(new_config)
        db.session.commit()
        flash('Alert Config created successfully!')
        return redirect(url_for('alert.list_configs'))
    return render_template('create_config.html', services=services,current_user=current_user)

@alert_bp.route('/configs/edit/<int:id>', methods=['GET', 'POST'])
def edit_config(id):
    config = AlertConfig.query.get_or_404(id)
    services = AlertService.query.all()
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    if request.method == 'POST':
        service_id = request.form['service_id']
        service = AlertService.query.get(service_id)
        config.company_id = request.form['company_id']
        config.service_id = service.id
        config.service_name = service.name
        config.group_name = request.form.get('group_name')
        config.group_id = request.form.get('group_id')
        config.auth_token = request.form.get('auth_token')
        config.status = bool(request.form.get('status'))
        config.api = request.form.get('api')
        config.api_key = request.form.get('api_key')
        config.senderid = request.form.get('senderid')
        db.session.commit()
        flash('Alert Config updated successfully!')
        return redirect(url_for('alert.list_configs'))
    return render_template('edit_config.html', config=config, services=services,current_user=current_user)

@alert_bp.route('/configs/delete/<int:id>', methods=['POST'])
def delete_config(id):
    config = AlertConfig.query.get_or_404(id)
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    db.session.delete(config)
    db.session.commit()
    flash('Alert Config deleted successfully!')
    return redirect(url_for('alert.list_configs'))


# ---------------- ALERT SAMPLE ----------------
@alert_bp.route('/samples')
def list_samples():
    print("Blueprint template folder:", alert_bp.template_folder)
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    samples = AlertSample.query.all()
    return render_template('list_samples.html', samples=samples, current_user=current_user)

@alert_bp.route('/samples/create', methods=['GET', 'POST'])
def create_sample():
    services = AlertService.query.all()
    configs = AlertConfig.query.all()
    users = User.query.all()
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)

    if request.method == 'POST':
        service = AlertService.query.get(request.form['service_id'])
        config = AlertConfig.query.get(request.form['config_id'])
        user = User.query.get(request.form.get('user_id')) if request.form.get('user_id') else None
        new_sample = AlertSample(
            company_id=request.form.get('company_id'),
            service_id=service.id,
            config_id=config.id,
            user_id=user.id if user else None,
            device_type_id=request.form.get('device_type_id'),
            title=request.form['title'],
            body=request.form.get('body'),
            single_user=bool(request.form.get('single_user')),
            is_common=bool(request.form.get('is_common')),
            category=int(request.form.get('category')),
        )
        db.session.add(new_sample)
        db.session.commit()
        flash('Alert Sample created successfully!')
        return redirect(url_for('alert.list_samples'))
    return render_template('create_sample.html', services=services, configs=configs, users=users,current_user=current_user)

@alert_bp.route('/samples/edit/<int:id>', methods=['GET', 'POST'])
def edit_sample(id):
    sample = AlertSample.query.get_or_404(id)
    services = AlertService.query.all()
    configs = AlertConfig.query.all()
    users = User.query.all()
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    if request.method == 'POST':
        service = AlertService.query.get(request.form['service_id'])
        config = AlertConfig.query.get(request.form['config_id'])
        user = User.query.get(request.form.get('user_id')) if request.form.get('user_id') else None

        sample.company_id = request.form.get('company_id')
        sample.service_id = service.id
        sample.config_id = config.id
        sample.user_id = user.id if user else None
        sample.device_type_id = request.form.get('device_type_id')
        sample.title = request.form['title']
        sample.body = request.form.get('body')
        sample.single_user = bool(request.form.get('single_user'))
        sample.is_common = bool(request.form.get('is_common'))
        sample.category = int(request.form.get('category'))
        db.session.commit()
        flash('Alert Sample updated successfully!')
        return redirect(url_for('alert.list_samples'))
    return render_template('edit_sample.html', sample=sample, services=services, configs=configs, users=users,current_user=current_user)

@alert_bp.route('/samples/delete/<int:id>', methods=['POST'])
def delete_sample(id):
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    sample = AlertSample.query.get_or_404(id)
    
    db.session.delete(sample)
    db.session.commit()
    flash('Alert Sample deleted successfully!')
    return redirect(url_for('alert.list_samples'))

