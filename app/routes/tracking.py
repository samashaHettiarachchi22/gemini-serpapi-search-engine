"""
Optimized Tracking Route
Single endpoint for tracking prompts and storing ALL dashboard analytics data
"""

from flask import Blueprint, request, jsonify
from app.models.optimized_tracking import search_tracking_db_optimized
from app.services.concurrent_collector import ConcurrentDataCollector
from app.services.gemini_service import GeminiService
from app.utils.logging_system import analytics_logger, execution_tracker
import time

tracking_bp = Blueprint('tracking', __name__)

# Initialize services
gemini_service = GeminiService()
concurrent_collector = None    # Will be initialized in init_tracking_services()


def init_tracking_services(gemini_api_key: str):
    """
    Initialize tracking services with API keys
    Call this from app factory

    """
    global concurrent_collector
    gemini_service.initialize(gemini_api_key)
    concurrent_collector = ConcurrentDataCollector(gemini_service)
    analytics_logger.log_info("Tracking services initialized")


@tracking_bp.route('/track-prompt', methods=['POST'])
def track_prompt():
    """
     SINGLE OPTIMIZED ENDPOINT: Track prompt and store ALL dashboard data
    
    Expected JSON:
        {
            "prompt": "your search query",
            "brand_domains": ["yourbrand.com"] (optional),
            "gl": "us" (optional),
            "hl": "en" (optional)
        }
    
    Task:
        1. Collect data from SerpAPI (concurrent)
        2. Analyze with Gemini (concurrent)
        3. Store ALL dashboard metrics in optimized tables
        4. Log execution and errors
        5. Return simple confirmation
    
    Returns:
        {
            "status": "success",
            "snapshot_id": 123,
            "message": "Data stored successfully",
            "execution_time_ms": 1234
        }
    """
    start_time = time.time()
    
    try:
        # === STEP 1: Validate Request ===
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            analytics_logger.log_warning("Invalid request: missing prompt")
            return jsonify({
                "status": "error",
                "message": "Missing required field: prompt"
            }), 400
        
        prompt = data['prompt']
        brand_domains = data.get('brand_domains', [])
        gl = data.get('gl', 'us')
        hl = data.get('hl', 'en')
        
        analytics_logger.log_info(
            f"Track prompt request received",
            extra={'prompt': prompt, 'brand_domains': brand_domains}
        )
        
        # === STEP 2: Check if concurrent collector is initialized ===
        if concurrent_collector is None:
            analytics_logger.log_critical("Concurrent collector not initialized")
            return jsonify({
                "status": "error",
                "message": "Service not initialized. Contact administrator."
            }), 500
        
        # === STEP 3: Reset execution tracker ===
        execution_tracker.reset()
        
        # === STEP 4: Collect ALL data concurrently ===
        try:
            structured_data = concurrent_collector.collect_all_data(
                prompt=prompt,
                brand_domains=brand_domains,
                gl=gl,
                hl=hl
            )
        except Exception as e:
            analytics_logger.log_critical(
                "Data collection failed",
                error=e,
                extra={'prompt': prompt}
            )
            return jsonify({
                "status": "error",
                "message": f"Data collection failed: {str(e)}"
            }), 500
        
        # === STEP 5: Store data in single transaction ===
        try:
            @execution_tracker.track_service('database')
            def store_data(query):
                # Calculate total processing time
                processing_time = int((time.time() - start_time) * 1000)
                structured_data['snapshot_data']['processing_time_ms'] = processing_time
                
                # Store everything in single transaction
                snapshot_id = search_tracking_db_optimized.save_complete_snapshot(
                    snapshot_data=structured_data['snapshot_data'],
                    citations_data=structured_data['citations_data'],
                    positions_data=structured_data['positions_data'],
                    log_data=structured_data['log_data']
                )
                return snapshot_id
            
            snapshot_id = store_data(query=prompt)
            
            analytics_logger.log_info(
                f"Data stored successfully",
                extra={'snapshot_id': snapshot_id, 'prompt': prompt}
            )
            
        except Exception as e:
            analytics_logger.log_critical(
                "Database storage failed",
                error=e,
                extra={'prompt': prompt}
            )
            return jsonify({
                "status": "error",
                "message": f"Storage failed: {str(e)}"
            }), 500
        
        # === STEP 6: Calculate total execution time ===
        end_time = time.time()
        total_execution_time = int((end_time - start_time) * 1000)
        
        # === STEP 7: Return simple success response ===
        return jsonify({
            "status": "success",
            "snapshot_id": snapshot_id,
            "message": "Data stored successfully",
            "execution_time_ms": total_execution_time,
            "timestamp": structured_data['snapshot_data']['timestamp'].isoformat()
        }), 200
        
    except Exception as e:
        # Catch-all error handler
        analytics_logger.log_critical(
            "Unexpected error in track_prompt",
            error=e
        )
        return jsonify({
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }), 500
