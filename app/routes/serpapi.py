from flask import Blueprint, request, jsonify, current_app
from app.services.serpapi_service import serpapi_service
from app.utils import success_response, error_response
import requests

serpapi_bp = Blueprint('serpapi', __name__)


@serpapi_bp.before_app_request
def initialize_serpapi():
    """Initialize SerpApi service before first request"""
    if not serpapi_service.api_key:
        api_key = current_app.config.get('SERPAPI_API_KEY')
        endpoint = current_app.config.get('SERPAPI_ENDPOINT')
        serpapi_service.initialize(api_key, endpoint)


@serpapi_bp.route('/answer-box', methods=['POST'])
def get_answer_box():
    """
    Get answer box or featured snippet from Google search
    
    Expected JSON body:
        {
            "query": "your search query",
            "gl": "us" (optional),
            "hl": "en" (optional),
            "google_domain": "google.com" (optional)
        }
    
    Returns:
        JSON response with answer box data or message if not found
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                "success": False,
                "error": "Missing required field: query"
            }), 400
        
        query = data['query']
        gl = data.get('gl', 'us')
        hl = data.get('hl', 'en')
        google_domain = data.get('google_domain', 'google.com')
        
        # Fetch search results
        search_results = serpapi_service.fetch_google_search(
            query=query,
            gl=gl,
            hl=hl,
            google_domain=google_domain
        )
        
        # Extract answer box
        answer_box = serpapi_service.extract_answer_box(search_results)
        
        if answer_box:
            return jsonify({
                "success": True,
                "query": query,
                "found": True,
                "data": answer_box
            })
        else:
            return jsonify({
                "success": True,
                "query": query,
                "found": False,
                "message": "No answer box or featured snippet found for this query"
            })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@serpapi_bp.route('/organic-results', methods=['POST'])
def get_organic_results():
    """
    Get traditional organic search results (blue links) from Google
    
    Expected JSON body:
        {
            "query": "your search query",
            "limit": 10 (optional, defaults to all),
            "gl": "us" (optional),
            "hl": "en" (optional),
            "google_domain": "google.com" (optional)
        }
    
    Returns:
        JSON response with organic results list
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                "success": False,
                "error": "Missing required field: query"
            }), 400
        
        query = data['query']
        limit = data.get('limit')
        gl = data.get('gl', 'us')
        hl = data.get('hl', 'en')
        google_domain = data.get('google_domain', 'google.com')
        
        # Fetch search results
        search_results = serpapi_service.fetch_google_search(
            query=query,
            gl=gl,
            hl=hl,
            google_domain=google_domain
        )
        
        # Extract organic results
        organic_results = serpapi_service.extract_organic_results(search_results, limit=limit)
        
        return jsonify({
            "success": True,
            "query": query,
            "count": len(organic_results),
            "results": organic_results
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== NEW ENDPOINT ====================

@serpapi_bp.route('/detect-features', methods=['POST'])
def detect_features():
    """
    Detect and extract all Google search features:
    - Knowledge Graph (info panel)
    - Answer Box (featured snippet)
    - AI Overview (AI-generated summary)
    - Organic Results (traditional blue links)
    
    Expected JSON body:
        {
            "query": "your search query",
            "limit_organic": 10 (optional, default: 10),
            "gl": "us" (optional),
            "hl": "en" (optional),
            "google_domain": "google.com" (optional)
        }
    
    Returns:
        Standardized JSON response with:
        - detection: Array [1/0, 1/0, 1/0, 1/0] for [KG, AB, AI, Organic]
        - Full data from each feature including organic results
    """
    try:
        data = request.get_json()
        
        # Validate request
        if not data or 'query' not in data:
            response, status_code = error_response(
                error="Missing required field: query",
                message="Invalid request",
                status_code=400,
                metadata={"required_fields": ["query"]}
            )
            return jsonify(response), status_code
        
        query = data['query']
        limit_organic = data.get('limit_organic', 10)
        gl = data.get('gl', 'us')
        hl = data.get('hl', 'en')
        google_domain = data.get('google_domain', 'google.com')
        
        # Fetch search results from SerpAPI
        search_results = serpapi_service.fetch_google_search(
            query=query,
            gl=gl,
            hl=hl,
            google_domain=google_domain
        )
        
        # Detect and extract all features including organic results
        features = serpapi_service.detect_and_extract_features(search_results, limit_organic=limit_organic)
        
        # Prepare metadata
        metadata = {
            "query": query,
            "country": gl,
            "language": hl,
            "google_domain": google_domain,
            "detection": features["detection"],
            "features_found": sum(features["detection"]),
            "features_detected": {
                "knowledge_graph": bool(features["detection"][0]),
                "answer_box": bool(features["detection"][1]),
                "ai_overview": bool(features["detection"][2]),
                "organic_results": bool(features["detection"][3])
            },
            "organic_results_count": features["organic_results_count"]
        }
        
        # Create response data
        response_data = {
            "knowledge_graph": features["knowledge_graph"],
            "answer_box": features["answer_box"],
            "ai_overview": features["ai_overview"],
            "organic_results": features["organic_results"]
        }
        
        # Return success response
        response, status_code = success_response(
            data=response_data,
            message="Features detected successfully",
            status_code=200,
            metadata=metadata
        )
        return jsonify(response), status_code
    
    except RuntimeError as e:
        response, status_code = error_response(
            error=str(e),
            message="Configuration error",
            status_code=500,
            metadata={"error_type": "RuntimeError"}
        )
        return jsonify(response), status_code
    
    except requests.RequestException as e:
        response, status_code = error_response(
            error=str(e),
            message="Failed to fetch search results",
            status_code=503,
            metadata={"error_type": "RequestException"}
        )
        return jsonify(response), status_code
    
    except Exception as e:
        response, status_code = error_response(
            error=str(e),
            message="Internal server error",
            status_code=500,
            metadata={"error_type": type(e).__name__}
        )
        return jsonify(response), status_code
