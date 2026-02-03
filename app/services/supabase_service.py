"""
JD2Q Supabase Service
Wrapper for Supabase client operations with error handling and RLS.
"""
from supabase import create_client, Client
from flask import current_app, g
from typing import Optional, Dict, List, Any
from datetime import datetime
from app.services.security_service import SecurityService


class SupabaseService:
    """Supabase client wrapper with helper methods."""
    
    _client: Optional[Client] = None
    _admin_client: Optional[Client] = None
    
    @classmethod
    def get_client(cls, use_service_role: bool = False) -> Client:
        """
        Get Supabase client instance.
        
        Args:
            use_service_role: If True, use service role key (bypasses RLS)
            
        Returns:
            Supabase client instance
        """
        url = current_app.config['SUPABASE_URL']
        
        if use_service_role:
            if cls._admin_client is None:
                key = current_app.config['SUPABASE_SERVICE_ROLE_KEY']
                cls._admin_client = create_client(url, key)
            return cls._admin_client
        else:
            if cls._client is None:
                key = current_app.config['SUPABASE_ANON_KEY']
                cls._client = create_client(url, key)
            return cls._client
    
    @staticmethod
    def sign_in_with_otp(email: str) -> Dict[str, Any]:
        """
        Send OTP email via Supabase Auth.
        
        Args:
            email: User email address
            
        Returns:
            Response data from Supabase
            
        Raises:
            Exception: If OTP sending fails
        """
        try:
            client = SupabaseService.get_client()
            response = client.auth.sign_in_with_otp({
                "email": email,
                "options": {
                    "should_create_user": True
                }
            })
            return response
        except Exception as e:
            raise Exception(f"Failed to send OTP: {str(e)}")
    
    @staticmethod
    def verify_otp(email: str, token: str) -> Dict[str, Any]:
        """
        Verify OTP token via Supabase Auth.
        
        Args:
            email: User email address
            token: OTP token from email
            
        Returns:
            Session data including user and access token
            
        Raises:
            Exception: If verification fails
        """
        try:
            client = SupabaseService.get_client()
            response = client.auth.verify_otp({
                "email": email,
                "token": token,
                "type": "email"
            })
            return response
        except Exception as e:
            raise Exception(f"Failed to verify OTP: {str(e)}")
    
    @staticmethod
    def sign_in_with_oauth(provider: str) -> str:
        """
        Get OAuth sign-in URL using PKCE flow.
        
        Args:
            provider: OAuth provider (e.g., 'google')
            
        Returns:
            OAuth authorization URL
        """
        client = SupabaseService.get_client()
        base_url = current_app.config.get('BASE_URL')
        
        # Fallback if BASE_URL is not configured
        if not base_url:
            from flask import request
            base_url = request.url_root.rstrip('/')
            
        response = client.auth.sign_in_with_oauth({
            "provider": provider,
            "options": {
                "redirect_to": f"{base_url}/auth/callback"
            }
        })
        return response.url
    
    @staticmethod
    def exchange_code_for_session(code: str) -> Any:
        """
        Exchange OAuth code for session (PKCE flow).
        
        Args:
            code: Auth code from callback query parameter
            
        Returns:
            AuthResponse including user and session
        """
        client = SupabaseService.get_client()
        response = client.auth.exchange_code_for_session({"auth_code": code})
        return response
    
    @staticmethod
    def sign_out(access_token: str = None):
        """
        Sign out user.
        
        Args:
            access_token: Optional access token to invalidate
        """
        try:
            client = SupabaseService.get_client()
            if access_token:
                client.auth.sign_out()
        except Exception:
            pass  # Ignore errors on logout
    
    @staticmethod
    def get_user(user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID from users table.
        
        Args:
            user_id: Supabase user ID
            
        Returns:
            User data or None if not found
        """
        try:
            client = SupabaseService.get_client()
            response = client.table('users').select('*').eq('id', user_id).maybe_single().execute()
            return response.data
        except Exception:
            return None
    
    @staticmethod
    def create_user(user_id: str, email: str, display_name: str = None) -> Dict[str, Any]:
        """
        Create user record in users table.
        
        Args:
            user_id: Supabase user ID from auth.users
            email: User email
            display_name: Optional display name
            
        Returns:
            Created user data
        """
        client = SupabaseService.get_client()
        data = {
            'id': user_id,
            'email': email,
            'display_name': display_name or email.split('@')[0],
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        response = client.table('users').insert(data).execute()
        return response.data[0] if response.data else None
    
    @staticmethod
    def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user record.
        
        Args:
            user_id: User ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated user data
        """
        client = SupabaseService.get_client()
        updates['updated_at'] = datetime.utcnow().isoformat()
        response = client.table('users').update(updates).eq('id', user_id).execute()
    def get_api_keys(user_id: str) -> List[Dict[str, Any]]:
        """
        Get all API keys for a user. Filters out soft-deleted keys.
        
        Args:
            user_id: User ID
            
        Returns:
            List of API key dictionaries
        """
        client = SupabaseService.get_client()
        response = client.table('api_keys').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        
        # Filter out keys that were soft-deleted (prefixed with [DELETED])
        keys = []
        for key in (response.data or []):
            if not key.get('key_name', '').startswith('[DELETED]'):
                keys.append(key)
        
        return keys
    
    @staticmethod
    def create_api_key(user_id: str, key_name: str, api_key: str) -> Dict[str, Any]:
        """
        Create encrypted API key record.
        
        Args:
            user_id: User ID
            key_name: Friendly name for the key
            api_key: Plaintext API key (will be encrypted)
            
        Returns:
            Created API key record
        """
        encrypted_key = SecurityService.encrypt_api_key(api_key)
        
        client = SupabaseService.get_client()
        data = {
            'user_id': user_id,
            'key_name': key_name,
            'encrypted_key': encrypted_key,
            'usage_count': 0,
            'created_at': datetime.utcnow().isoformat()
        }
        response = client.table('api_keys').insert(data).execute()
        return response.data[0] if response.data else None
    
    @staticmethod
    def delete_api_key(key_id: str, user_id: str):
        """
        Delete API key. If it has history, renames it with [DELETED] prefix
        to avoid FK violations while preserving data integrity.
        
        Args:
            key_id: API key ID
            user_id: User ID (for ownership check)
        """
        client = SupabaseService.get_client()
        
        try:
            # 1. Try to delete directly
            client.table('api_keys').delete().eq('id', key_id).eq('user_id', user_id).execute()
        except Exception:
            # 2. If it fails (due to FK constraint from generation_requests),
            # we perform a "soft delete" by renaming the key so it stays in DB for history 
            # but is hidden from the user's key list.
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
            client.table('api_keys').update({
                'key_name': f"[DELETED] {timestamp}"
            }).eq('id', key_id).eq('user_id', user_id).execute()
    
    @staticmethod
    def increment_key_usage(key_id: str):
        """
        Increment usage counter for API key.
        
        Args:
            key_id: API key ID
        """
        client = SupabaseService.get_client(use_service_role=True)
        # Use service role to bypass RLS for increment operation
        client.rpc('increment_key_usage', {'key_id': key_id}).execute()
    
    @staticmethod
    def create_generation_request(user_id: str, api_key_id: str, job_description: str) -> Dict[str, Any]:
        """
        Create generation request record.
        
        Args:
            user_id: User ID
            api_key_id: API key ID used
            job_description: Job description text
            
        Returns:
            Created generation request
        """
        client = SupabaseService.get_client()
        data = {
            'user_id': user_id,
            'api_key_id': api_key_id,
            'job_description': job_description,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        response = client.table('generation_requests').insert(data).execute()
        return response.data[0] if response.data else None
    
    @staticmethod
    def update_generation_request(gen_id: str, updates: Dict[str, Any]):
        """
        Update generation request.
        
        Args:
            gen_id: Generation request ID
            updates: Fields to update
        """
        client = SupabaseService.get_client()
        client.table('generation_requests').update(updates).eq('id', gen_id).execute()
    
    @staticmethod
    def get_generation_request(gen_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Get generation request by ID.
        
        Args:
            gen_id: Generation request ID
            user_id: Optional user ID for ownership check
            
        Returns:
            Generation request data or None
        """
        client = SupabaseService.get_client()
        query = client.table('generation_requests').select('*').eq('id', gen_id)
        
        if user_id:
            query = query.eq('user_id', user_id)
        
        response = query.maybe_single().execute()
        return response.data
    
    @staticmethod
    def get_user_generations(user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get generation history for user.
        
        Args:
            user_id: User ID
            limit: Number of records to return
            offset: Offset for pagination
            
        Returns:
            List of generation requests
        """
        client = SupabaseService.get_client()
        response = (client.table('generation_requests')
                   .select('*')
                   .eq('user_id', user_id)
                   .order('created_at', desc=True)
                   .limit(limit)
                   .offset(offset)
                   .execute())
        return response.data or []
    
    @staticmethod
    def create_questions(generation_id: str, questions: List[Dict[str, Any]]):
        """
        Bulk create questions for a generation.
        
        Args:
            generation_id: Generation request ID
            questions: List of question data dicts
        """
        client = SupabaseService.get_client()
        
        records = []
        for q in questions:
            records.append({
                'generation_id': generation_id,
                'question_id': q.get('id'),
                'section_title': q.get('section_title'),
                'skill': q.get('skill'),
                'question_type': q.get('type'),
                'difficulty': q.get('difficulty'),
                'question_text': q.get('text'),
                'expected_signals': q.get('expected_signals', []),
                'created_at': datetime.utcnow().isoformat()
            })
        
        if records:
            client.table('questions').insert(records).execute()
    
    @staticmethod
    def get_questions_for_generation(generation_id: str) -> List[Dict[str, Any]]:
        """
        Get all questions for a generation.
        
        Args:
            generation_id: Generation request ID
            
        Returns:
            List of questions
        """
        client = SupabaseService.get_client()
        response = (client.table('questions')
                   .select('*')
                   .eq('generation_id', generation_id)
                   .order('created_at')
                   .execute())
        return response.data or []
    
    @staticmethod
    def update_question_answer(question_id: str, answer: str):
        """
        Update generated answer for a question.
        
        Args:
            question_id: Question ID
            answer: Generated answer text
        """
        client = SupabaseService.get_client()
        client.table('questions').update({'generated_answer': answer}).eq('id', question_id).execute()
    
    @staticmethod
    def log_activity(user_id: str, action: str, entity_type: str = None, 
                    entity_id: str = None, metadata: Dict = None):
        """
        Log user activity.
        
        Args:
            user_id: User ID
            action: Action description
            entity_type: Type of entity acted upon
            entity_id: ID of entity
            metadata: Additional metadata
        """
        try:
            client = SupabaseService.get_client()
            data = {
                'user_id': user_id,
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            client.table('activity_logs').insert(data).execute()
        except Exception:
            pass  # Don't fail operations due to logging errors

    @staticmethod
    def toggle_favorite(user_id: str, question_id: str) -> bool:
        """
        Toggle favorite status for a question.
        
        Args:
            user_id: User ID
            question_id: Question ID
            
        Returns:
            True if favored, False if unfavored
        """
        client = SupabaseService.get_client()
        
        # Check if exists
        existing = (client.table('favorites')
                   .select('*')
                   .eq('user_id', user_id)
                   .eq('question_id', question_id)
                   .maybe_single()
                   .execute())
        
        if existing.data:
            # Delete if exists
            client.table('favorites').delete().eq('id', existing.data['id']).execute()
            return False
        else:
            # Create if not exists
            client.table('favorites').insert({
                'user_id': user_id,
                'question_id': question_id
            }).execute()
            return True

    @staticmethod
    def get_user_favorites(user_id: str) -> List[Dict[str, Any]]:
        """
        Get all favorites for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of favorite questions with details
        """
        client = SupabaseService.get_client()
        
        # Get favorite entries
        favs = (client.table('favorites')
               .select('question_id, created_at')
               .eq('user_id', user_id)
               .execute())
        
        if not favs.data:
            return []
            
        question_ids = [f['question_id'] for f in favs.data]
        
        # Get actual questions
        questions = (client.table('questions')
                    .select('*')
                    .in_('id', question_ids)
                    .execute())
                    
        return questions.data or []


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from session.
    Cached in flush global 'g' to prevent duplicate DB calls.
    
    Returns:
        User data or None if not authenticated
    """
    if 'current_user' in g:
        return g.current_user

    user_id = SecurityService.get_session_user_id()
    if not user_id:
        g.current_user = None
        return None
    
    user = SupabaseService.get_user(user_id)
    g.current_user = user
    return user


def login_required(f):
    """
    Decorator to require authentication for routes.
    
    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            ...
    """
    from functools import wraps
    from flask import redirect, url_for, flash
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not SecurityService.is_authenticated():
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Verify user exists in database (handle stale sessions)
        user = get_current_user()
        if not user:
            SecurityService.clear_session()
            flash('Session expired or invalid. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    
    return decorated_function
