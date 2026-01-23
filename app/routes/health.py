from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)

@health_bp.route('/')
def home():
    """API home endpoint"""
    return jsonify({
        "message": "Gemini AI Backend API",
        "version": "1.0.0",
        "endpoints": {
            "/": "GET - API information",
            "/health": "GET - Health check",
            "/api/models": "GET - List available Gemini models",
            "/api/generate": "POST - Generate AI response"
        }
    })

@health_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Gemini AI Backend"
    })
