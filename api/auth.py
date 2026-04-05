"""
Authentication routes — register, login, profile, alert settings.
JWT tokens are used (valid for 7 days).
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt
from datetime import timedelta
from api.database import db
from api.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user account.
    ---
    tags: [Authentication]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password]
          properties:
            email: {type: string, example: user@example.com}
            password: {type: string, example: mypassword123}
    responses:
      201: {description: Account created}
      400: {description: Invalid input}
      409: {description: Email already registered}
    """
    data = request.get_json() or {}
    email    = data.get('email', '').lower().strip()
    password = data.get('password', '')

    if not email or '@' not in email:
        return jsonify({'error': 'Valid email is required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user    = User(email=email, password_hash=pw_hash, alert_email=email)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=7))
    return jsonify({'message': 'Account created', 'access_token': token, 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login and receive a JWT token.
    ---
    tags: [Authentication]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password]
          properties:
            email: {type: string}
            password: {type: string}
    responses:
      200: {description: Login successful}
      401: {description: Invalid credentials}
    """
    data     = request.get_json() or {}
    email    = data.get('email', '').lower().strip()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=7))
    return jsonify({'message': 'Login successful', 'access_token': token, 'user': user.to_dict()})


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Get current user profile (requires login).
    ---
    tags: [Authentication]
    security: [{Bearer: []}]
    responses:
      200: {description: User profile}
      401: {description: Not authenticated}
    """
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()})


@auth_bp.route('/update-alerts', methods=['PUT'])
@jwt_required()
def update_alerts():
    """Update email alert preferences.
    ---
    tags: [Authentication]
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
        if 0 < t <= 1:
            user.alert_threshold = t

    db.session.commit()
    return jsonify({'message': 'Alert settings updated', 'user': user.to_dict()})
