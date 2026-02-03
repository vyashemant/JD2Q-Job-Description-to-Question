"""
JD2Q AI Service
Google Gemini API integration for question and answer generation.
"""
import json
import os
from typing import Dict, List, Any, Optional
from flask import current_app
import google.generativeai as genai
from app.services.security_service import SecurityService

print("\n" + "="*50)
print("DEBUG: JD2Q AI Service Loaded Successfully")
print("="*50 + "\n")


class AIService:
    """Service for interacting with Google Gemini API."""
    
    # Cache for prompt templates
    _prompts_cache = {}
    
    @staticmethod
    def load_prompt_template(template_name: str) -> Dict[str, Any]:
        """
        Load prompt template from JSON file.
        
        Args:
            template_name: Template file name (without .json extension)
            
        Returns:
            Prompt template dictionary
        """
        if template_name in AIService._prompts_cache:
            return AIService._prompts_cache[template_name]
        
        # Get prompts directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        prompts_dir = os.path.join(base_dir, 'prompts')
        template_path = os.path.join(prompts_dir, f'{template_name}.json')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        
        AIService._prompts_cache[template_name] = template
        return template
    
    @staticmethod
    def configure_client(api_key: str):
        """
        Configure Gemini client with API key.
        
        Args:
            api_key: Decrypted Gemini API key
        """
        if api_key:
            genai.configure(api_key=api_key.strip())
    
    @staticmethod
    def generate_questions(job_description: str, encrypted_api_key: str) -> Dict[str, Any]:
        """
        Generate interview questions from job description.
        
        Args:
            job_description: Job description text
            encrypted_api_key: Encrypted Gemini API key
            
        Returns:
            Dictionary with role_level, extracted_skills, and sections
            
        Raises:
            Exception: If generation fails or response doesn't match schema
        """
        try:
            # Decrypt API key
            api_key = SecurityService.decrypt_api_key(encrypted_api_key)
            if not api_key:
                raise Exception("Decrypted API key is EMPTY")
            
            api_key = api_key.strip()
            key_prefix = api_key[:5] + "..." + api_key[-4:] if len(api_key) > 10 else "SHORT"
            
            # CRITICAL LOGGING FOR DEBUGGING
            print(f"\n[AI SERVICE] Generating questions...")
            print(f"[AI SERVICE] Model: models/gemini-2.5-flash")
            print(f"[AI SERVICE] Using Key: {key_prefix}")
            
            AIService.configure_client(api_key)
            
            # Load prompt template
            template = AIService.load_prompt_template('v1_structured')
            
            # Build prompt
            min_questions = current_app.config.get('MIN_QUESTIONS', 15)
            user_prompt = template['user_template'].replace(
                '{{job_description}}', job_description
            ).replace(
                '{{min_questions}}', str(min_questions)
            )
            
            # Configure model
            model = genai.GenerativeModel(
                model_name='models/gemini-2.5-flash',
                system_instruction=template['system_instruction']
            )
            
            # Generate content
            response = model.generate_content(
                user_prompt,
                generation_config={
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'top_k': 40,
                    'max_output_tokens': 8192,
                    'response_mime_type': 'application/json'
                }
            )
            
            # Parse response
            result = json.loads(response.text)
            
            # Validate schema
            AIService._validate_question_response(result, min_questions)
            
            return result
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            # Include key prefix to diagnose if it's the right key
            try:
                msg = f"Question generation failed (gemini-2.5-flash | Key: {key_prefix}): {str(e)}"
            except:
                msg = f"Question generation failed (gemini-2.5-flash): {str(e)}"
            raise Exception(msg)
    
    @staticmethod
    def generate_answer(question_data: Dict[str, Any], encrypted_api_key: str) -> str:
        """
        Generate model answer for a specific question.
        
        Args:
            question_data: Dictionary with question details (text, type, difficulty, etc.)
            encrypted_api_key: Encrypted Gemini API key
            
        Returns:
            Generated answer text
            
        Raises:
            Exception: If answer generation fails
        """
        try:
            # Decrypt API key
            api_key = SecurityService.decrypt_api_key(encrypted_api_key)
            AIService.configure_client(api_key)
            
            # Load prompt template
            template = AIService.load_prompt_template('answer_template')
            
            # Build prompt
            user_prompt = template['user_template']
            replacements = {
                '{{role_level}}': question_data.get('role_level', 'Mid-level'),
                '{{skill}}': question_data.get('skill', 'General'),
                '{{question_type}}': question_data.get('type', 'Conceptual'),
                '{{difficulty}}': question_data.get('difficulty', 'Mid-level'),
                '{{question_text}}': question_data.get('text', ''),
                '{{expected_signals}}': '\n'.join(f"- {signal}" for signal in question_data.get('expected_signals', []))
            }
            
            for placeholder, value in replacements.items():
                user_prompt = user_prompt.replace(placeholder, value)
            
            # Configure model
            model = genai.GenerativeModel(
                model_name='models/gemini-2.5-flash',
                system_instruction=template['system_instruction']
            )
            
            # Generate content
            response = model.generate_content(
                user_prompt,
                generation_config={
                    'temperature': 0.8,
                    'top_p': 0.95,
                    'max_output_tokens': 1024
                }
            )
            
            return response.text.strip()
            
        except Exception as e:
            raise Exception(f"Answer generation failed (gemini-2.5-flash): {str(e)}")
    
    @staticmethod
    def _validate_question_response(response: Dict[str, Any], min_questions: int):
        """
        Validate response matches expected schema.
        
        Args:
            response: Parsed JSON response
            min_questions: Minimum number of questions required
            
        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        required_fields = ['role_level', 'extracted_skills', 'sections']
        for field in required_fields:
            if field not in response:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate sections structure
        if not isinstance(response['sections'], list) or len(response['sections']) == 0:
            raise ValueError("Response must contain at least one section")
        
        # Count total questions
        total_questions = 0
        for section in response['sections']:
            if 'questions' not in section:
                raise ValueError(f"Section '{section.get('title', 'Unknown')}' missing questions")
            
            questions = section['questions']
            if not isinstance(questions, list):
                raise ValueError(f"Questions must be a list in section '{section.get('title', 'Unknown')}'")
            
            total_questions += len(questions)
            
            # Validate each question
            for question in questions:
                required_q_fields = ['id', 'type', 'difficulty', 'text', 'expected_signals']
                for field in required_q_fields:
                    if field not in question:
                        raise ValueError(f"Question missing required field: {field}")
        
        # Check minimum questions
        if total_questions < 1:
            raise ValueError("AI failed to generate any questions. Please check the job description and try again.")
        
        if total_questions < min_questions:
            # Log a warning instead of failing
            try:
                current_app.logger.warning(
                    f"AI generated only {total_questions} questions, which is less than the requested {min_questions}. "
                    "Proceeding with partial result."
                )
            except Exception:
                pass
    
    @staticmethod
    def test_api_key(api_key: str) -> tuple[bool, str]:
        """
        Test if an API key is valid by making a simple request.
        
        Args:
            api_key: Plaintext API key to test
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # First, check if the key is structurally valid (basic check)
            if not api_key or len(api_key) < 10:
                return False, "Malformed API key"

            AIService.configure_client(api_key)
            
            # Use gemini-2.5-flash as the standard probe model (best for free tier)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            # Simple probe
            response = model.generate_content(
                "Say 'ok'.",
                generation_config={
                    'max_output_tokens': 10,
                    'temperature': 0.0
                }
            )
            
            # Deterministic check:
            # If we got candidates, the key is structurally valid and authorized.
            # Even if all candidates are blocked by safety filters (finish_reason=3 or 4),
            # or if the response is empty (finish_reason=2), the key itself is valid.
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                # Key is valid because the request was accepted and processed
                return True, ""
                
            # If we can't see candidates but didn't get an exception, 
            # we should still try to check if it's a valid Auth object
            return True, ""
                
        except Exception as e:
            error_msg = str(e)
            
            # Specific Google API error codes
            if '403' in error_msg or 'PERMISSION_DENIED' in error_msg:
                return False, f"Permission Denied: {error_msg}"
            elif '400' in error_msg or 'API_KEY_INVALID' in error_msg:
                return False, "Invalid API key structure or key has been revoked."
            elif '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg:
                return False, "API quota exceeded for this key."
            elif '404' in error_msg or 'MODEL_NOT_FOUND' in error_msg:
                # Fallback: maybe the model name is wrong? 
                # But if it reached this point, the key might still be valid
                return True, "Note: Model not found, but key appears valid."
            
            return False, f"API test failed: {error_msg}"


def flatten_questions(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten nested question structure for easier database storage.
    
    Args:
        result: Structured response from AI
        
    Returns:
        List of question dictionaries with section info
    """
    questions = []
    
    for section in result.get('sections', []):
        section_title = section.get('title')
        section_skill = section.get('skill')
        
        for question in section.get('questions', []):
            questions.append({
                'id': question.get('id'),
                'section_title': section_title,
                'skill': section_skill,
                'type': question.get('type'),
                'difficulty': question.get('difficulty'),
                'text': question.get('text'),
                'expected_signals': question.get('expected_signals', [])
            })
    
    return questions
