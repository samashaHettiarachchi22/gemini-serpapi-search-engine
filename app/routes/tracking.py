"""
Simplified Tracking Routes
Direct calls to collectors - no factory pattern
"""

from flask import Blueprint, request, jsonify
from app.models.optimized_tracking import search_tracking_db_optimized
from app.services.concurrent_collector import ConcurrentDataCollector
from app.services.gemini_service import gemini_service
from app.services.gemini_only_collector import GeminiOnlyCollector
from app.services.claude_collector import claude_collector
from app.services.claude_service import claude_service
from app.services.serpapi_service import serpapi_service
from app.services.serp_gemini_service import serp_gemini_service
from app.utils.logging_system import analytics_logger
import time

tracking_bp = Blueprint('tracking', __name__)

# Initialize services
concurrent_collector = None
gemini_only_collector = None
claude_service_available = False


def init_tracking_services(gemini_api_key: str, claude_api_key: str = None):
    """Initialize tracking services with API keys"""
    global concurrent_collector, gemini_only_collector, claude_service_available
    
    # Initialize Gemini
    gemini_service.initialize(gemini_api_key)
    concurrent_collector = ConcurrentDataCollector(gemini_service)
    gemini_only_collector = GeminiOnlyCollector()
    
    # Initialize SerpAPI (required for serp_gemini)
    from flask import current_app
    serpapi_key = current_app.config.get('SERPAPI_API_KEY')
    serpapi_endpoint = current_app.config.get('SERPAPI_ENDPOINT')
    if serpapi_key:
        serpapi_service.initialize(serpapi_key, serpapi_endpoint)
        serp_gemini_service.initialize(serpapi_key, gemini_api_key, serpapi_endpoint)
        analytics_logger.log_info("SerpAPI and SerpGemini services initialized")
    
    # Initialize Claude if key provided
    if claude_api_key:
        claude_service.initialize(claude_api_key)
        claude_service_available = True
        analytics_logger.log_info("Claude service initialized")
    
    analytics_logger.log_info("Tracking services initialized")



@tracking_bp.route('/gemini-only', methods=['POST'])
def track_gemini_only():
    """
    GEMINI ONLY: Just provide prompt
    
    Expected JSON:
        {
            "prompt": "your search query",
            "brand_domains": ["example.com"] (optional)
        }
    
    Returns:
        {
            "status": "success",
            "snapshot_id": 123,
            "metrics": {...},
            "execution_time_ms": 1234
        }
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"status": "error", "message": "Missing prompt"}), 400
        
        prompt = data['prompt']
        brand_domains = data.get('brand_domains', [])
        
        analytics_logger.log_info(f"Processing Gemini-only request", extra={'prompt': prompt})
        
        # Direct call to collector - NO FACTORY!
        result = gemini_only_collector.collect_gemini_snapshot(
            query=prompt,
            brand_domains=brand_domains,
            gl=data.get('gl', 'us'),
            hl=data.get('hl', 'en')
        )
        
        return jsonify(result)
        
    except Exception as e:
        analytics_logger.log_error(f"Gemini-only track failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }), 500


@tracking_bp.route('/claude-only', methods=['POST'])
def track_claude_only():
    """
    CLAUDE ONLY: Just provide prompt
    
    Expected JSON:
        {
            "prompt": "your search query",
            "brand_domains": ["example.com"] (optional)
        }
    
    Returns:
        {
            "status": "success",
            "snapshot_id": 123,
            "metrics": {...},
            "execution_time_ms": 1234
        }
    """
    start_time = time.time()
    
    try:
        if not claude_service_available:
            return jsonify({
                "status": "error",
                "message": "Claude service not available - API key not configured"
            }), 503
        
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"status": "error", "message": "Missing prompt"}), 400
        
        prompt = data['prompt']
        brand_domains = data.get('brand_domains', [])
        
        analytics_logger.log_info(f"Processing Claude-only request", extra={'prompt': prompt})
        
        # Direct call to Claude collector - same format as Gemini!
        result = claude_collector.collect_claude_snapshot(
            query=prompt,
            brand_domains=brand_domains
        )
        
        return jsonify(result)
        
    except Exception as e:
        analytics_logger.log_error(f"Claude-only track failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }), 500


@tracking_bp.route('/gemini-serp', methods=['POST'])
def track_gemini_serp():
    """
    GEMINI + SERPAPI: Full search analysis
    
    Expected JSON:
        {
            "prompt": "your search query",
            "brand_domains": ["example.com"] (optional),
            "gl": "us" (optional),
            "hl": "en" (optional)
        }
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"status": "error", "message": "Missing prompt"}), 400
        
        prompt = data['prompt']
        brand_domains = data.get('brand_domains', [])
        gl = data.get('gl', 'us')
        hl = data.get('hl', 'en')
        
        analytics_logger.log_info(f"Processing Gemini+SERP request", extra={'prompt': prompt})
        
        # Direct call to concurrent collector - NO FACTORY!
        structured_data = concurrent_collector.collect_all_data(
            prompt=prompt,
            brand_domains=brand_domains,
            gl=gl,
            hl=hl
        )
        
        # Save to database
        snapshot_id = search_tracking_db_optimized.save_complete_snapshot(
            snapshot_data=structured_data['snapshot_data'],
            citations_data=structured_data['citations_data'],
            positions_data=structured_data['positions_data'],
            log_data={
                "query": prompt,
                "gemini_status": "success",
                "serpapi_status": "success",
                "database_status": "success",
                "total_time_ms": int((time.time() - start_time) * 1000),
                "log_level": "INFO"
            }
        )
        
        return jsonify({
            "status": "success",
            "snapshot_id": snapshot_id,
            "category": "gemini-serp",
            "execution_time_ms": int((time.time() - start_time) * 1000)
        })
        
    except Exception as e:
        analytics_logger.log_error(f"Gemini-SERP track failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }), 500


@tracking_bp.route('/compare-all', methods=['POST'])
def compare_all_services():
    """
    COMPARE ALL SERVICES: Send same prompt to Claude, Gemini, and SerpGemini
    Returns standardized responses from all three services
    
    Expected JSON:
        {
            "prompt": "your query",
            "gl": "us" (optional, for serp_gemini),
            "hl": "en" (optional, for serp_gemini),
            "model": "optional model name"
        }
    
    Returns:
        {
            "status": "success",
            "prompt": "your query",
            "results": {
                "claude": {...standardized response...},
                "gemini": {...standardized response...},
                "serp_gemini": {...standardized response...}
            },
            "summary": {
                "total_time_ms": 3456,
                "total_cost": 0.0045,
                "services_success": ["claude", "gemini", "serp_gemini"],
                "services_failed": []
            }
        }
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"status": "error", "message": "Missing prompt"}), 400
        
        prompt = data['prompt']
        model = data.get('model')
        gl = data.get('gl', 'us')
        hl = data.get('hl', 'en')
        
        analytics_logger.log_info(f"Comparing all services for prompt", extra={'prompt': prompt})
        
        results = {}
        services_success = []
        services_failed = []
        total_cost = 0
        
        # Call Claude
        try:
            claude_response = claude_service.generate_content(prompt, model=model)
            results['claude'] = claude_response
            if claude_response.get('status') == 'success':
                services_success.append('claude')
                total_cost += claude_response.get('metadata', {}).get('cost', 0) or 0
            else:
                services_failed.append('claude')
        except Exception as e:
            analytics_logger.log_error(f"Claude failed: {str(e)}")
            results['claude'] = {
                "service": "claude",
                "status": "error",
                "prompt": prompt,
                "response": None,
                "error": str(e)
            }
            services_failed.append('claude')
        
        # Call Gemini
        try:
            gemini_response = gemini_service.generate_content(prompt, model=model)
            results['gemini'] = gemini_response
            if gemini_response.get('status') == 'success':
                services_success.append('gemini')
                total_cost += gemini_response.get('metadata', {}).get('cost', 0) or 0
            else:
                services_failed.append('gemini')
        except Exception as e:
            analytics_logger.log_error(f"Gemini failed: {str(e)}")
            results['gemini'] = {
                "service": "gemini",
                "status": "error",
                "prompt": prompt,
                "response": None,
                "error": str(e)
            }
            services_failed.append('gemini')
        
        # Call SerpGemini
        try:
            serp_gemini_response = serp_gemini_service.search_and_process(
                query=prompt,
                gl=gl,
                hl=hl,
                model=model
            )
            results['serp_gemini'] = serp_gemini_response
            if serp_gemini_response.get('status') == 'success':
                services_success.append('serp_gemini')
                total_cost += serp_gemini_response.get('metadata', {}).get('cost', 0) or 0
            else:
                services_failed.append('serp_gemini')
        except Exception as e:
            analytics_logger.log_error(f"SerpGemini failed: {str(e)}")
            results['serp_gemini'] = {
                "service": "serp_gemini",
                "status": "error",
                "prompt": prompt,
                "response": None,
                "error": str(e)
            }
            services_failed.append('serp_gemini')
        
        total_time_ms = int((time.time() - start_time) * 1000)
        
        return jsonify({
            "status": "success",
            "prompt": prompt,
            "results": results,
            "summary": {
                "total_time_ms": total_time_ms,
                "total_cost": round(total_cost, 6),
                "services_success": services_success,
                "services_failed": services_failed,
                "success_count": len(services_success),
                "failed_count": len(services_failed)
            }
        })
        
    except Exception as e:
        analytics_logger.log_error(f"Compare-all failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }), 500

