"""
Authentication routes using Clerk.
The frontend handles Sign-In/Sign-Up, and the backend verifies the Clerk Session Token.
"""
from flask import Blueprint, request, jsonify, g
from functools import wraps
from api.database import db
from api.models import User
from api.clerk_client import clerk_client

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def clerk_required(f):
    """
    Decorator to protect routes with Clerk Authentication.
    Verifies the session token and syncs the Clerk user to our local database.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Verify the request using Clerk Backend SDK
            request_state = clerk_client.authenticate_request(request)
            if not request_state.is_signed_in:
                return jsonify({'error': 'Unauthorized. Please sign in with Clerk.'}), 401
            
            # Extract Clerk ID from the token (the 'sub' claim)
            clerk_id = request_state.payload.get('sub')
            
            # Sync local user database
            user = User.query.filter_by(clerk_id=clerk_id).first()
            if not user:
                # First-time user: In a real app, you might fetch full user object from Clerk
                # Here we'll just use the data available in the token or set a placeholder
                # Note: Configure your Clerk Dashboard to include 'email' in the session token claims
                email = request_state.payload.get('email', 'user_via_clerk@example.com')
                user = User(clerk_id=clerk_id, email=email, alert_email=email)
                db.session.add(user)
                db.session.commit()
            
            # Store user in Flask 'g' for accessibility in route handlers
            g.user = user
            
        except Exception as e:
            return jsonify({'error': f'Authentication Failed: {str(e)}'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

# Register and Login routes are now handled by Clerk Frontend SDK.
# Removing deprecated register/login endpoints.

@auth_bp.route('/me', methods=['GET'])
@clerk_required
def me():
    """Get current user profile (synced from Clerk)."""
    return jsonify({'user': g.user.to_dict()})

@auth_bp.route('/update-alerts', methods=['PUT'])
@clerk_required
def update_alerts():
    """Update email alert preferences for the current user."""
    data = request.get_json() or {}
    if 'alert_email'    in data: g.user.alert_email    = data['alert_email']
    if 'alerts_enabled' in data: g.user.alerts_enabled = bool(data['alerts_enabled'])
    if 'alert_threshold' in data:
        try:
            t = float(data['alert_threshold'])
            if 0 < t <= 1:
                g.user.alert_threshold = t
        except ValueError:
            pass

    db.session.commit()
    return jsonify({'message': 'Alert settings updated', 'user': g.user.to_dict()})
