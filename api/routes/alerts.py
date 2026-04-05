"""
Alert configuration routes — get/update settings, send test email.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from api.database import db
from api.models import User
from api.utils.email_helper import send_test_email

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alerts')


@alerts_bp.route('/config', methods=['GET'])
@jwt_required()
def get_config():
    """Get current alert configuration.
    ---
    tags: [Alerts]
    security: [{Bearer: []}]
    """
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'alert_email':     user.alert_email or user.email,
        'alert_threshold': user.alert_threshold,
        'alerts_enabled':  user.alerts_enabled,
    })


@alerts_bp.route('/config', methods=['PUT'])
@jwt_required()
def update_config():
    """Update alert settings.
    ---
    tags: [Alerts]
    security: [{Bearer: []}]
    """
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}
    if 'alert_email'    in data: user.alert_email    = data['alert_email']
    if 'alerts_enabled' in data: user.alerts_enabled = bool(data['alerts_enabled'])
    if 'alert_threshold' in data:
        t = float(data['alert_threshold'])
        if 0 < t <= 1: user.alert_threshold = t

    db.session.commit()
    return jsonify({'message': 'Settings updated'})


@alerts_bp.route('/test', methods=['POST'])
@jwt_required()
def test_alert():
    """Send a test alert email to verify configuration.
    ---
    tags: [Alerts]
    security: [{Bearer: []}]
    """
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'User not found'}), 404

    target = user.alert_email or user.email
    ok     = send_test_email(target)
    if ok:
        return jsonify({'message': f'Test email sent to {target}'})
    return jsonify({'error': 'Failed to send email. Check MAIL_PASSWORD in your .env or Render env vars.'}), 500
