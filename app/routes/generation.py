"""
JD2Q Generation Routes
Job description input and question generation flow.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.services.supabase_service import login_required, SupabaseService
from app.services.security_service import SecurityService, validate_jd_word_count
from app.services.ai_service import AIService, flatten_questions
from app.extensions import limiter

generation_bp = Blueprint('generation', __name__)


@generation_bp.route('/', methods=['GET'])
@login_required
def index():
    """Display job description input form."""
    user_id = SecurityService.get_session_user_id()
    
    # Check if user has API keys
    api_keys = SupabaseService.get_api_keys(user_id)
    
    if not api_keys:
        flash('Please add at least one Gemini API key before generating questions.', 'warning')
        return redirect(url_for('profile.add_key'))
    
    return render_template('generation/input.html', api_keys=api_keys)


@generation_bp.route('/generate', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def generate():
    """Generate questions from job description."""
    user_id = SecurityService.get_session_user_id()
    
    # Get form data
    job_description = request.form.get('job_description', '').strip()
    api_key_id = request.form.get('api_key_id', '').strip()
    
    if not job_description or not api_key_id:
        flash('Please provide both job description and select an API key.', 'error')
        return redirect(url_for('generation.index'))
    
    # Validate word count
    is_valid, word_count = validate_jd_word_count(job_description)
    if not is_valid:
        max_words = 1500  # From config
        flash(f'Job description too long ({word_count} words). Maximum is {max_words} words.', 'error')
        return redirect(url_for('generation.index'))
    
    try:
        # Get API key
        api_keys = SupabaseService.get_api_keys(user_id)
        selected_key = next((k for k in api_keys if k['id'] == api_key_id), None)
        
        if not selected_key:
            flash('Invalid API key selected.', 'error')
            return redirect(url_for('generation.index'))
        
        # Create generation request
        gen_request = SupabaseService.create_generation_request(
            user_id=user_id,
            api_key_id=api_key_id,
            job_description=job_description
        )
        
        gen_id = gen_request['id']
        
        # Generate questions
        result = AIService.generate_questions(
            job_description=job_description,
            encrypted_api_key=selected_key['encrypted_key']
        )
        
        # Update generation request with results
        SupabaseService.update_generation_request(gen_id, {
            'status': 'completed',
            'role_level': result.get('role_level'),
            'extracted_skills': result.get('extracted_skills')
        })
        
        # Store questions
        questions = flatten_questions(result)
        SupabaseService.create_questions(gen_id, questions)
        
        # Increment API key usage
        SupabaseService.increment_key_usage(api_key_id)
        
        # Log activity
        SupabaseService.log_activity(
            user_id, 'generate_questions', 'generation_request', gen_id,
            {'word_count': word_count, 'question_count': len(questions)}
        )
        
        flash(f'Successfully generated {len(questions)} questions!', 'success')
        return redirect(url_for('generation.results', gen_id=gen_id))
        
    except Exception as e:
        # Update request as failed
        if 'gen_id' in locals():
            SupabaseService.update_generation_request(gen_id, {
                'status': 'failed',
                'error_message': str(e)
            })
        
        flash(f'Question generation failed: {str(e)}', 'error')
        return redirect(url_for('generation.index'))


@generation_bp.route('/results/<gen_id>')
@login_required
def results(gen_id):
    """Display generated questions."""
    user_id = SecurityService.get_session_user_id()
    
    # Get generation request
    gen_request = SupabaseService.get_generation_request(gen_id, user_id)
    
    if not gen_request:
        flash('Generation not found.', 'error')
        return redirect(url_for('web.dashboard'))
    
    # Get questions
    questions = SupabaseService.get_questions_for_generation(gen_id)
    
    # Group by section
    sections = {}
    for question in questions:
        section_title = question.get('section_title', 'General')
        if section_title not in sections:
            sections[section_title] = []
        sections[section_title].append(question)
    
    return render_template(
        'generation/results.html',
        generation=gen_request,
        sections=sections,
        total_questions=len(questions)
    )


@generation_bp.route('/regenerate/<gen_id>', methods=['POST'])
@login_required
@limiter.limit("3 per minute")
def regenerate(gen_id):
    """Regenerate questions from an existing generation request."""
    user_id = SecurityService.get_session_user_id()
    
    # Get original generation request
    original_gen = SupabaseService.get_generation_request(gen_id, user_id)
    
    if not original_gen:
        flash('Original generation not found.', 'error')
        return redirect(url_for('web.dashboard'))
        
    # Reuse parameters
    job_description = original_gen['job_description']
    api_key_id = original_gen['api_key_id']
    
    try:
        # Get API key
        api_keys = SupabaseService.get_api_keys(user_id)
        selected_key = next((k for k in api_keys if k['id'] == api_key_id), None)
        
        if not selected_key:
            flash('Original API key usage not authorized or key deleted.', 'error')
            return redirect(url_for('generation.index'))
        
        # Create NEW generation request (avoid overwrite for history)
        gen_request = SupabaseService.create_generation_request(
            user_id=user_id,
            api_key_id=api_key_id,
            job_description=job_description
        )
        
        new_gen_id = gen_request['id']
        
        # Generate questions
        result = AIService.generate_questions(
            job_description=job_description,
            encrypted_api_key=selected_key['encrypted_key']
        )
        
        # Update generation request
        SupabaseService.update_generation_request(new_gen_id, {
            'status': 'completed',
            'role_level': result.get('role_level'),
            'extracted_skills': result.get('extracted_skills')
        })
        
        # Store questions
        questions = flatten_questions(result)
        SupabaseService.create_questions(new_gen_id, questions)
        
        # Increment usage
        SupabaseService.increment_key_usage(api_key_id)
        
        # Log activity
        SupabaseService.log_activity(
            user_id, 'regenerate_questions', 'generation_request', new_gen_id,
            {'original_gen_id': gen_id, 'question_count': len(questions)}
        )
        
        flash(f'Successfully regenerated questions!', 'success')
        return redirect(url_for('generation.results', gen_id=new_gen_id))
        
    except Exception as e:
        if 'new_gen_id' in locals():
            SupabaseService.update_generation_request(new_gen_id, {
                'status': 'failed',
                'error_message': str(e)
            })
        flash(f'Regeneration failed: {str(e)}', 'error')
        return redirect(url_for('generation.results', gen_id=gen_id))


@generation_bp.route('/answer/<question_id>', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def generate_answer(question_id):
    """Generate model answer for a question (AJAX endpoint)."""
    user_id = SecurityService.get_session_user_id()
    
    try:
        # Get question details using list query (more reliable than maybe_single for some environments)
        client = SupabaseService.get_client()
        question_res = client.table('questions').select('*').eq('id', question_id).execute()
        
        if not question_res.data:
            return jsonify({'error': 'Question entries not found for this ID'}), 404
        
        question_data = question_res.data[0]
        
        # Verify ownership via generation request
        gen_res = client.table('generation_requests').select('user_id, api_key_id').eq('id', question_data['generation_id']).execute()
        
        if not gen_res.data:
            return jsonify({'error': 'Generation record missing'}), 404
            
        gen_data = gen_res.data[0]
        if gen_data['user_id'] != user_id:
            return jsonify({'error': 'Access Denied: You do not own this generation record'}), 403
        
        # Check if answer already exists
        if question_data.get('generated_answer'):
            return jsonify({'answer': question_data['generated_answer']})
        
        # Get API key record separately for reliability
        key_res = client.table('api_keys').select('encrypted_key').eq('id', gen_data['api_key_id']).execute()
        
        if not key_res.data:
            return jsonify({'error': 'Associated API key has been deleted or is missing'}), 404
            
        encrypted_key = key_res.data[0]['encrypted_key']
        
        # Prepare question data for answer generation
        answer_data = {
            'role_level': question_data.get('difficulty', 'Mid-level'),
            'skill': question_data.get('skill', 'General'),
            'type': question_data.get('question_type', 'Conceptual'),
            'difficulty': question_data.get('difficulty', 'Mid-level'),
            'text': question_data.get('question_text', ''),
            'expected_signals': question_data.get('expected_signals', [])
        }
        
        # Generate answer
        answer = AIService.generate_answer(answer_data, encrypted_key)
        
        # Save answer
        SupabaseService.update_question_answer(question_id, answer)
        
        # Log activity
        SupabaseService.log_activity(user_id, 'generate_answer', 'question', question_id)
        
        return jsonify({'answer': answer})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
