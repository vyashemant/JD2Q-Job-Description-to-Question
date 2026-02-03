"""
JD2Q Web Routes
Main public pages and dashboard.
"""
from flask import Blueprint, render_template
from app.services.supabase_service import login_required, get_current_user

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def index():
    """Homepage."""
    from flask import request, redirect, url_for
    # Fallback for Google OAuth if it redirects to root instead of callback
    if request.args.get('code'):
        return redirect(url_for('auth.oauth_callback', code=request.args.get('code')))
        
    return render_template('web/index.html')


@web_bp.route('/about')
def about():
    """About page."""
    return render_template('web/about.html')


@web_bp.route('/docs')
def docs():
    """Documentation page."""
    return render_template('web/docs.html')


@web_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    user = get_current_user()
    from app.services.supabase_service import SupabaseService
    favorites = SupabaseService.get_user_favorites(user['id']) if user else []
    return render_template('web/dashboard.html', user=user, favorites=favorites)


@web_bp.route('/favorite/<question_id>', methods=['POST'])
@login_required
def toggle_favorite(question_id):
    """Toggle favorite status for a question."""
    from flask import jsonify
    from app.services.supabase_service import SupabaseService, SecurityService
    
    user_id = SecurityService.get_session_user_id()
    is_favored = SupabaseService.toggle_favorite(user_id, question_id)
    
    return jsonify({'favored': is_favored})
