"""
JD2Q Profile Routes
User profile management and API key CRUD.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.services.supabase_service import login_required, SupabaseService, get_current_user
from app.services.security_service import SecurityService
from app.services.ai_service import AIService
from werkzeug.utils import secure_filename
import os

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/')
@login_required
def view():
    """View user profile."""
    user = get_current_user()
    return render_template('profile/view.html', user=user)


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    """Edit user profile."""
    user = get_current_user()
    
    if request.method == 'GET':
        return render_template('profile/edit.html', user=user)
    
    # POST - update profile
    display_name = request.form.get('display_name', '').strip()
    
    try:
        user_id = SecurityService.get_session_user_id()
        SupabaseService.update_user(user_id, {'display_name': display_name})
        
        SupabaseService.log_activity(user_id, 'update_profile', 'user', user_id)
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.view'))
        
    except Exception as e:
        flash(f'Failed to update profile: {str(e)}', 'error')
        return render_template('profile/edit.html', user=user)


@profile_bp.route('/keys')
@login_required
def keys():
    """List user's API keys."""
    user_id = SecurityService.get_session_user_id()
    api_keys = SupabaseService.get_api_keys(user_id)
    
    # Mask keys for display
    for key in api_keys:
        key['masked_key'] = SecurityService.mask_api_key(key['encrypted_key'], visible_chars=8)
    
    return render_template('profile/keys.html', api_keys=api_keys)


@profile_bp.route('/keys/add', methods=['GET', 'POST'])
@login_required
def add_key():
    """Add new API key."""
    if request.method == 'GET':
        return render_template('profile/add_key.html')
    
    # POST - create API key
    user_id = SecurityService.get_session_user_id()
    key_name = request.form.get('key_name', '').strip()
    api_key = request.form.get('api_key', '').strip()
    
    if not key_name or not api_key:
        flash('Please provide both a name and API key.', 'error')
        return render_template('profile/add_key.html')
    
    try:
        # Test API key first
        is_valid, error_msg = AIService.test_api_key(api_key)
        
        if not is_valid:
            flash(f'API key validation failed: {error_msg}', 'error')
            return render_template('profile/add_key.html')
        
        # Create encrypted key
        SupabaseService.create_api_key(user_id, key_name, api_key)
        
        SupabaseService.log_activity(user_id, 'create_api_key', 'api_key', None, {'key_name': key_name})
        
        flash('API key added successfully!', 'success')
        return redirect(url_for('profile.keys'))
        
    except Exception as e:
        flash(f'Failed to add API key: {str(e)}', 'error')
        return render_template('profile/add_key.html')


@profile_bp.route('/keys/<key_id>/delete', methods=['POST'])
@login_required
def delete_key(key_id):
    """Delete API key."""
    user_id = SecurityService.get_session_user_id()
    
    try:
        SupabaseService.delete_api_key(key_id, user_id)
        
        SupabaseService.log_activity(user_id, 'delete_api_key', 'api_key', key_id)
        
        flash('API key deleted successfully.', 'success')
    except Exception as e:
        flash(f'Failed to delete API key: {str(e)}', 'error')
    
    return redirect(url_for('profile.keys'))


@profile_bp.route('/keys/test', methods=['POST'])
@login_required
def test_key():
    """Test API key validity (AJAX endpoint)."""
    data = request.get_json()
    api_key = data.get('api_key', '').strip()
    
    if not api_key:
        return jsonify({'valid': False, 'error': 'API key is required'}), 400
    
    is_valid, error_msg = AIService.test_api_key(api_key)
    
    if is_valid:
        return jsonify({'valid': True, 'message': 'API key is valid!'})
    else:
        return jsonify({'valid': False, 'error': error_msg})
