from flask import Blueprint, jsonify, request
from app.models.optimized_tracking import search_tracking_db_optimized

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
            "/api/stats": "GET - API usage statistics (all services)",
            "/api/tracking/gemini-only": "POST - Gemini AI analysis",
            "/api/tracking/gemini-serp": "POST - Gemini + Google search",
            "/api/tracking/claude-only": "POST - Claude AI analysis"
        }
    })

@health_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Gemini AI Backend"
    })

@health_bp.route('/api/stats')
def get_all_stats():
    """
    Get API usage statistics for ALL services (Gemini, Claude, SerpAPI)
    
    Query params:
        days: Number of days to look back (default: 7)
        service: Filter by specific service: 'gemini', 'claude', 'serpapi' (optional, default: all)
    
    Returns:
        JSON response with statistics
    """
    try:
        days = request.args.get('days', default=7, type=int)
        service = request.args.get('service', default=None, type=str)
        
        # Get stats - if service is None, gets all services
        stats = search_tracking_db_optimized.get_api_stats(service=service, days=days)
        
        return jsonify({
            "success": True,
            "days": days,
            "service": service if service else "all",
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
