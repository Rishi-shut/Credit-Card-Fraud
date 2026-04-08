"""
Authentication routes using Clerk.
The frontend handles Sign-In/Sign-Up, and the backend verifies the Clerk Session Token.
"""
from flask import Blueprint, request, jsonify, g
from functools import wraps
from api.database import db
from api.models import User
from api.clerk_client import clerk_client
from clerk_backend_api.security import AuthenticateRequestOptions

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
            options = AuthenticateRequestOptions()
            request_state = clerk_client.authenticate_request(request, options)
            if not request_state.is_signed_in:
                return jsonify({'error': 'Unauthorized. Please sign in with Clerk.'}), 401
            
            # Extract Clerk ID from the token (the 'sub' claim)
            clerk_id = request_state.payload.get('sub')
            
            # PRO-ACTIVE FETCH: Get the full user object from Clerk Backend API
            # Note: We use the sync client here.
            try:
                clerk_user = clerk_client.users.get(user_id=clerk_id)
                email = None
                
                # Try to get the primary email
                if hasattr(clerk_user, 'email_addresses') and clerk_user.email_addresses:
                    # In some versions it's a list of objects with an 'email_address' attribute
                    email = clerk_user.email_addresses[0].email_address
                elif isinstance(clerk_user, dict) and 'email_addresses' in clerk_user:
                    email = clerk_user['email_addresses'][0].get('email_address')
                
                if not email:
                    # Last resort fallback to token
                    email = request_state.payload.get('email')
            except Exception as fetch_err:
                print(f"[AUTH DEBUG] Clerk API fetch failed: {str(fetch_err)}")
                email = request_state.payload.get('email')

            if not email:
                email = 'user_via_clerk@example.com'
            
            # Sync local user database
            user = User.query.filter_by(clerk_id=clerk_id).first()
            if not user:
                user = User(clerk_id=clerk_id, email=email)
                db.session.add(user)
            elif user.email != email and email != 'user_via_clerk@example.com':
                user.email = email
            
            # Automatically crown the owner account with Developer/Admin powers
            import os
            admin_email = os.environ.get('ADMIN_EMAIL', 'mriganksingh792005@gmail.com').strip().lower()
            current_email = email.strip().lower()

            # DEBUG LOGS
            print(f"[AUTH DEBUG] Clerk ID: {clerk_id}")
            print(f"[AUTH DEBUG] Current Email: '{current_email}'")
            print(f"[AUTH DEBUG] Target Admin: '{admin_email}'")
            
            if current_email == admin_email:
                user.is_admin = True
                user.dev_status = 'approved'
                print(f"[AUTH DEBUG] SUCCESS: Admin privileges granted to {current_email}")
                
            db.session.commit()
            
            # Store user in Flask 'g' for accessibility in route handlers
            g.user = user
            g.clerk_user_id = clerk_id
            
        except Exception as e:
            import traceback
            print(f"[AUTH DEBUG] Auth Logic Failure: {str(e)}")
            traceback.print_exc()
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
