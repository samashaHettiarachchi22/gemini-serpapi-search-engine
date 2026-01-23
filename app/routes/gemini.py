from flask import Blueprint, request, jsonify, current_app
from app.services.gemini_service import gemini_service

gemini_bp = Blueprint('gemini', __name__)

@gemini_bp.before_app_request
def initialize_gemini():
    """Initialize Gemini service before first request"""
    if not gemini_service.client:
        api_key = current_app.config.get('GEMINI_API_KEY')
        gemini_service.initialize(api_key)

@gemini_bp.route('/models', methods=['GET'])
def list_models():
    """
    List all available Gemini models
    
    Returns:
        JSON response with list of models or error
    """
    try:
        model_names = gemini_service.list_models()
        return jsonify({
            "success": True,
            "count": len(model_names),
            "models": model_names
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@gemini_bp.route('/generate', methods=['POST'])
def generate():
    """
    Generate AI response from a prompt
    
    Expected JSON body:
        {
            "prompt": "Your prompt here",
            "model": "models/gemini-2.5-flash" (optional)
        }
    
    Returns:
        JSON response with generated text or error
    """
    try:
        data = request.get_json()
        
        # Validate request
        if not data or 'prompt' not in data:
            return jsonify({
                "success": False,
                "error": "Please provide a 'prompt' in the request body"
            }), 400
        
        prompt = data['prompt']
        model = data.get('model')  # Optional custom model
        
        # Generate content
        response_text = gemini_service.generate_content(prompt, model)
        
        return jsonify({
            "success": True,
            "prompt": prompt,
            "response": response_text
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
