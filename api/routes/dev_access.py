"""
Developer Access and Admin API Routes
"""
from flask import Blueprint, jsonify, session, g
from api.database import db
from api.models import User
from api.auth import clerk_required

dev_bp = Blueprint('dev', __name__, url_prefix='/api/dev')

# ─── Ordinary User Routes ──────────────────────────────────────────

@dev_bp.route('/status', methods=['GET'])
@clerk_required
def get_status():
    """Get the current developer access status for the logged in user."""
    user = User.query.filter_by(clerk_id=g.clerk_user_id).first()
    if not user:
        return jsonify({'error': 'User not found in DB'}), 404
        
    return jsonify({
        'dev_status': user.dev_status,
        'is_admin': user.is_admin
    })


@dev_bp.route('/request', methods=['POST'])
@clerk_required
def request_access():
    """Allows a user to request developer access."""
    user = User.query.filter_by(clerk_id=g.clerk_user_id).first()
    if not user:
        return jsonify({'error': 'User not found in DB'}), 404
        
    if user.dev_status in ['pending', 'approved']:
        return jsonify({'error': f'Request already {user.dev_status}'}), 400
        
    user.dev_status = 'pending'
    db.session.commit()
    return jsonify({'message': 'Access requested successfully', 'status': 'pending'})


@dev_bp.route('/generate-session', methods=['POST'])
@clerk_required
def generate_session():
    """Generates a secure Flask session cookie if dev access is approved."""
    user = User.query.filter_by(clerk_id=g.clerk_user_id).first()
    if not user:
        return jsonify({'error': 'User not found in DB'}), 404
        
    if user.dev_status == 'approved' or user.is_admin:
        session['dev_auth'] = True
        return jsonify({'message': 'Session generated. You may now access /apidocs.'})
        
    return jsonify({'error': 'You do not have approved developer access.'}), 403


# ─── Admin Routes ──────────────────────────────────────────────────

@dev_bp.route('/admin/requests', methods=['GET'])
@clerk_required
def list_requests():
    """List all developer access requests (pending and approved). Admin only."""
    user = User.query.filter_by(clerk_id=g.clerk_user_id).first()
    if not user or not user.is_admin:
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403
        
    # Fetch both pending and approved to allow management
    users = User.query.filter(User.dev_status != 'none', User.is_admin == False).all()
    return jsonify([u.to_dict() for u in users])


@dev_bp.route('/admin/requests/<int:target_id>/approve', methods=['POST'])
@clerk_required
def approve_request(target_id):
    """Approve a developer access request. Admin only."""
    user = User.query.filter_by(clerk_id=g.clerk_user_id).first()
    if not user or not user.is_admin:
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403
        
    target = User.query.get(target_id)
    if not target:
        return jsonify({'error': 'Target user not found.'}), 404
        
    target.dev_status = 'approved'
    db.session.commit()
    return jsonify({'message': f'Approved developer access for {target.email}.'})


@dev_bp.route('/admin/requests/<int:target_id>/reject', methods=['POST'])
@clerk_required
def reject_request(target_id):
    """Reject a developer access request. Admin only."""
    user = User.query.filter_by(clerk_id=g.clerk_user_id).first()
    if not user or not user.is_admin:
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403
        
    target = User.query.get(target_id)
    if not target:
        return jsonify({'error': 'Target user not found.'}), 404
        
    target.dev_status = 'rejected'
    db.session.commit()
    return jsonify({'message': f'Rejected developer access for {target.email}.'})


@dev_bp.route('/admin/requests/<int:target_id>/revoke', methods=['POST'])
@clerk_required
def revoke_access(target_id):
    """Revoke approved developer access. Admin only."""
    user = User.query.filter_by(clerk_id=g.clerk_user_id).first()
    if not user or not user.is_admin:
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403
        
    target = User.query.get(target_id)
    if not target:
        return jsonify({'error': 'Target user not found.'}), 404
        
    target.dev_status = 'none'
    db.session.commit()
    return jsonify({'message': f'Revoked developer access for {target.email}.'})

