"""
JD2Q History Routes
Generation history viewing and export functionality.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, make_response, jsonify, request
from app.services.supabase_service import login_required, SupabaseService
from app.services.security_service import SecurityService
import csv
import io
import json
from datetime import datetime

history_bp = Blueprint('history', __name__)


@history_bp.route('/')
@login_required
def index():
    """List generation history."""
    user_id = SecurityService.get_session_user_id()
    
    # Get pagination params
    page = int(request.args.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page
    
    # Get generations
    generations = SupabaseService.get_user_generations(user_id, limit=per_page, offset=offset)
    
    return render_template('history/index.html', generations=generations, page=page)


@history_bp.route('/<gen_id>')
@login_required
def view(gen_id):
    """View specific generation with all questions."""
    user_id = SecurityService.get_session_user_id()
    
    gen_request = SupabaseService.get_generation_request(gen_id, user_id)
    
    if not gen_request:
        flash('Generation not found.', 'error')
        return redirect(url_for('history.index'))
    
    questions = SupabaseService.get_questions_for_generation(gen_id)
    
    # Group by section
    sections = {}
    for question in questions:
        section_title = question.get('section_title', 'General')
        if section_title not in sections:
            sections[section_title] = {
                'title': section_title,
                'skill': question.get('skill'),
                'questions': []
            }
        sections[section_title]['questions'].append(question)
    
    return render_template(
        'history/view.html',
        generation=gen_request,
        sections=sections.values(),
        total_questions=len(questions)
    )


@history_bp.route('/<gen_id>/export/json')
@login_required
def export_json(gen_id):
    """Export questions as JSON."""
    user_id = SecurityService.get_session_user_id()
    
    gen_request = SupabaseService.get_generation_request(gen_id, user_id)
    
    if not gen_request:
        return jsonify({'error': 'Generation not found'}), 404
    
    questions = SupabaseService.get_questions_for_generation(gen_id)
    
    # Build export structure
    export_data = {
        'generation_id': gen_id,
        'created_at': gen_request.get('created_at'),
        'role_level': gen_request.get('role_level'),
        'extracted_skills': gen_request.get('extracted_skills'),
        'job_description': gen_request.get('job_description'),
        'questions': questions
    }
    
    # Create response
    response = make_response(json.dumps(export_data, indent=2))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=questions_{gen_id}.json'
    
    # Log activity
    SupabaseService.log_activity(user_id, 'export_json', 'generation_request', gen_id)
    
    return response


@history_bp.route('/<gen_id>/export/csv')
@login_required
def export_csv(gen_id):
    """Export questions as CSV."""
    user_id = SecurityService.get_session_user_id()
    
    gen_request = SupabaseService.get_generation_request(gen_id, user_id)
    
    if not gen_request:
        flash('Generation not found.', 'error')
        return redirect(url_for('history.index'))
    
    questions = SupabaseService.get_questions_for_generation(gen_id)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Question ID', 'Section', 'Skill', 'Type', 'Difficulty',
        'Question', 'Expected Signals', 'Model Answer'
    ])
    
    # Rows
    for q in questions:
        writer.writerow([
            q.get('question_id', ''),
            q.get('section_title', ''),
            q.get('skill', ''),
            q.get('question_type', ''),
            q.get('difficulty', ''),
            q.get('question_text', ''),
            ', '.join(q.get('expected_signals', [])),
            q.get('generated_answer', '')
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=questions_{gen_id}.csv'
    
    # Log activity
    SupabaseService.log_activity(user_id, 'export_csv', 'generation_request', gen_id)
    
    return response


@history_bp.route('/<gen_id>/export/pdf')
@login_required
def export_pdf(gen_id):
    """Export questions as PDF."""
    # Note: For simplicity, we'll redirect to a print-friendly page
    # In production, you'd use reportlab or weasyprint
    user_id = SecurityService.get_session_user_id()
    
    gen_request = SupabaseService.get_generation_request(gen_id, user_id)
    
    if not gen_request:
        flash('Generation not found.', 'error')
        return redirect(url_for('history.index'))
    
    questions = SupabaseService.get_questions_for_generation(gen_id)
    
    # Group by section
    sections = {}
    for question in questions:
        section_title = question.get('section_title', 'General')
        if section_title not in sections:
            sections[section_title] = []
        sections[section_title].append(question)
    
    # Log activity
    SupabaseService.log_activity(user_id, 'export_pdf', 'generation_request', gen_id)
    
    return render_template(
        'history/print.html',
        generation=gen_request,
        sections=sections,
        total_questions=len(questions)
    )
