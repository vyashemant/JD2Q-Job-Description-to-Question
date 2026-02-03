"""
JD2Q Authentication Routes
Handles OTP and OAuth authentication via Supabase.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services.supabase_service import SupabaseService, get_current_user
from app.services.security_service import SecurityService
from app.extensions import limiter
from flask import current_app

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET'])
def login():
    """Display login page with OTP and OAuth options."""
    # Redirect if already logged in with valid session
    if SecurityService.is_authenticated():
        if get_current_user():
            return redirect(url_for('web.dashboard'))
        # Clear stale session
        SecurityService.clear_session()
    
    return render_template('auth/login.html')


@auth_bp.route('/send-otp', methods=['POST'])
@limiter.limit("500 per minute")
def send_otp():
    """Send OTP email via Supabase Auth."""
    email = request.form.get('email', '').strip().lower()
    
    if not email:
        flash('Please provide an email address.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Send OTP via Supabase
        SupabaseService.sign_in_with_otp(email)
        
        # Store email in session for verification
        session['otp_email'] = email
        
        flash(f'Verification code sent to {email}. Please check your inbox.', 'success')
        return redirect(url_for('auth.verify_otp'))
        
    except Exception as e:
        current_app.logger.error(f"OTP send failure for {email}: {str(e)}")
        flash(f'Failed to send verification code: {str(e)}', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """Verify OTP token."""
    email = session.get('otp_email')
    
    if not email:
        flash('Please request a verification code first.', 'warning')
        return redirect(url_for('auth.login'))
    
    if request.method == 'GET':
        return render_template('auth/verify_otp.html', email=email)
    
    # POST - verify the token
    otp_token = request.form.get('otp_token', '').strip()
    
    if not otp_token:
        flash('Please enter the verification code.', 'error')
        return render_template('auth/verify_otp.html', email=email)
    
    try:
        # Verify OTP via Supabase
        response = SupabaseService.verify_otp(email, otp_token)
        
        # Extract user and session data
        user = response.user
        access_token = response.session.access_token if response.session else None
        
        # Create or get user record
        user_record = SupabaseService.get_user(user.id)
        if not user_record:
            display_name = user.email.split('@')[0]
            if hasattr(user, 'user_metadata') and isinstance(user.user_metadata, dict):
                display_name = user.user_metadata.get('full_name', display_name)
                
            user_record = SupabaseService.create_user(
                user_id=user.id,
                email=user.email,
                display_name=display_name
            )
        
        # Set session
        SecurityService.set_user_session(user.id, user.email, access_token)
        
        # Log activity
        SupabaseService.log_activity(user.id, 'login', 'auth', user.id, {'method': 'otp'})
        
        # Clear OTP email from session
        session.pop('otp_email', None)
        
        flash('Successfully logged in!', 'success')
        return redirect(url_for('web.dashboard'))
        
    except Exception as e:
        current_app.logger.warning(f"OTP verification failed for {email}: {str(e)}")
        flash(f'Verification failed: {str(e)}', 'error')
        return render_template('auth/verify_otp.html', email=email)


@auth_bp.route('/google')
def google_oauth():
    """Initiate Google OAuth flow."""
    try:
        auth_url = SupabaseService.sign_in_with_oauth('google')
        return redirect(auth_url)
    except Exception as e:
        flash(f'OAuth initiation failed: {str(e)}', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/callback')
def oauth_callback():
    """Handle OAuth callback from Supabase."""
    # Check for 'code' query parameter (PKCE flow)
    code = request.args.get('code')
    
    if code:
        try:
            # Exchange code for session
            response = SupabaseService.exchange_code_for_session(code)
            
            # Extract user and session data
            user = response.user
            session_obj = response.session
            access_token = session_obj.access_token if session_obj else None
            
            if not user or not access_token:
                flash('Authentication failed: No user or token received.', 'error')
                return redirect(url_for('auth.login'))
            
            # Create or get user record
            user_record = SupabaseService.get_user(user.id)
            
            if not user_record:
                display_name = None
                if hasattr(user, 'user_metadata'):
                    if isinstance(user.user_metadata, dict):
                        display_name = user.user_metadata.get('full_name')
                
                user_record = SupabaseService.create_user(
                    user_id=user.id,
                    email=user.email,
                    display_name=display_name
                )
            
            # Set Flask session
            SecurityService.set_user_session(user.id, user.email, access_token)
            
            # Log activity
            SupabaseService.log_activity(user.id, 'login', 'auth', user.id, {'method': 'oauth_google_pkce'})
            
            flash('Successfully logged in with Google!', 'success')
            return redirect(url_for('web.dashboard'))
            
        except Exception as e:
            current_app.logger.error(f"Google OAuth callback error: {str(e)}")
            flash(f'Authentication failed: {str(e)}', 'error')
            return redirect(url_for('auth.login'))
            
    # If no code, fall back to hash fragment flow (Implicit flow)
    # Must be extracted client-side via JavaScript
    return render_template('auth/oauth_callback.html')


@auth_bp.route('/set-session', methods=['POST'])
def set_session():
    """
    Set Flask session from OAuth callback (called via AJAX).
    Receives access token from client-side JavaScript.
    """
    data = request.get_json()
    access_token = data.get('access_token')
    
    if not access_token:
        return {'error': 'Missing access token'}, 400
    
    try:
        # Get user from Supabase using access token
        client = SupabaseService.get_client()
        user_response = client.auth.get_user(access_token)
        user = user_response.user
        
        if not user:
            return {'error': 'Invalid access token'}, 400
        
        # Create or get user record
        user_record = SupabaseService.get_user(user.id)
        if not user_record:
            display_name = user.email.split('@')[0]
            if hasattr(user, 'user_metadata') and isinstance(user.user_metadata, dict):
                display_name = user.user_metadata.get('full_name', display_name)
            
            user_record = SupabaseService.create_user(
                user_id=user.id,
                email=user.email,
                display_name=display_name
            )
        
        # Set Flask session
        SecurityService.set_user_session(user.id, user.email, access_token)
        
        # Log activity
        SupabaseService.log_activity(user.id, 'login', 'auth', user.id, {'method': 'oauth_google'})
        
        return {'success': True, 'redirect': url_for('web.dashboard')}
        
    except Exception as e:
        return {'error': str(e)}, 400


@auth_bp.route('/logout')
def logout():
    """Log out user."""
    # Get access token before clearing session
    access_token = SecurityService.get_session_access_token()
    user_id = SecurityService.get_session_user_id()
    
    # Log activity before logout
    if user_id:
        SupabaseService.log_activity(user_id, 'logout', 'auth', user_id)
    
    # Sign out from Supabase
    if access_token:
        SupabaseService.sign_out(access_token)
    
    # Clear session
    SecurityService.clear_session()
    
    flash('You have been logged out.', 'info')
    return redirect(url_for('web.index'))
