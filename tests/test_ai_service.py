"""
Tests for AI service prompt loading and validation.
"""
import pytest
import json
from app.services.ai_service import AIService, flatten_questions


def test_load_prompt_template():
    """Test loading prompt templates."""
    template = AIService.load_prompt_template('v1_structured')
    
    assert 'version' in template
    assert 'system_instruction' in template
    assert 'user_template' in template
    assert 'response_schema' in template
    
    # Verify schema structure
    schema = template['response_schema']
    assert schema['type'] == 'object'
    assert 'role_level' in schema['required']
    assert 'extracted_skills' in schema['required']
    assert 'sections' in schema['required']


def test_validate_question_response():
    """Test question response validation."""
    valid_response = {
        'role_level': 'Senior',
        'extracted_skills': ['Python', 'Flask'],
        'sections': [
            {
                'title': 'Framework Knowledge',
                'skill': 'Flask',
                'questions': [
                    {
                        'id': 'q1',
                        'type': 'Conceptual',
                        'difficulty': 'Senior',
                        'text': 'Explain Flask contexts',
                        'expected_signals': ['app context', 'request context']
                    }
                ]
            }
        ]
    }
    
    # Should not raise exception
    AIService._validate_question_response(valid_response, min_questions=1)
    

def test_validate_question_response_missing_fields():
    """Test validation fails with missing fields."""
    invalid_response = {
        'role_level': 'Senior',
        # Missing extracted_skills and sections
    }
    
    with pytest.raises(ValueError, match="Missing required field"):
        AIService._validate_question_response(invalid_response, min_questions=1)


def test_validate_question_response_too_few_questions():
    """Test validation succeeds with few questions (soft validation)."""
    response = {
        'role_level': 'Senior',
        'extracted_skills': ['Python'],
        'sections': [
            {
                'title': 'Test',
                'skill': 'Python',
                'questions': [
                    {
                        'id': 'q1',
                        'type': 'Conceptual',
                        'difficulty': 'Senior',
                        'text': 'Test question',
                        'expected_signals': ['signal1']
                    }
                ]
            }
        ]
    }
    
    # Should NOT raise exception anymore due to soft validation
    AIService._validate_question_response(response, min_questions=15)


def test_validate_question_response_zero_questions():
    """Test validation still fails with zero questions."""
    response = {
        'role_level': 'Senior',
        'extracted_skills': ['Python'],
        'sections': [
            {
                'title': 'Test',
                'skill': 'Python',
                'questions': []
            }
        ]
    }
    
    with pytest.raises(ValueError, match="AI failed to generate any questions"):
        AIService._validate_question_response(response, min_questions=15)


def test_flatten_questions():
    """Test flattening nested question structure."""
    result = {
        'role_level': 'Senior',
        'extracted_skills': ['Python', 'Flask'],
        'sections': [
            {
                'title': 'Framework Knowledge',
                'skill': 'Flask',
                'questions': [
                    {
                        'id': 'q1',
                        'type': 'Conceptual',
                        'difficulty': 'Senior',
                        'text': 'Question 1',
                        'expected_signals': ['signal1', 'signal2']
                    },
                    {
                        'id': 'q2',
                        'type': 'Practical',
                        'difficulty': 'Mid-level',
                        'text': 'Question 2',
                        'expected_signals': ['signal3']
                    }
                ]
            }
        ]
    }
    
    questions = flatten_questions(result)
    
    assert len(questions) == 2
    assert questions[0]['id'] == 'q1'
    assert questions[0]['section_title'] == 'Framework Knowledge'
    assert questions[0]['skill'] == 'Flask'
    assert questions[1]['id'] == 'q2'
