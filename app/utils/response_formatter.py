"""
Response formatter utility for consistent API responses
"""
from datetime import datetime
from typing import Any, Dict, Optional


class StandardServiceResponse:
    """
    Unified response format for all AI services (Claude, Gemini, SerpGemini)
    Ensures consistent structure regardless of which service is used
    """
    
    @staticmethod
    def format_service_response(
        service_name: str,
        prompt: str,
        response_text: str,
        status: str = "success",
        model: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cost: Optional[float] = None,
        search_results: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        cached: bool = False,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create standardized response format for all services
        
        Args:
            service_name: "claude", "gemini", or "serp_gemini"
            prompt: User's input prompt
            response_text: AI's response text
            status: "success" or "error"
            model: Model name (or None)
            response_time_ms: Response time in milliseconds (or None)
            tokens_used: Total tokens used (or None)
            input_tokens: Input tokens (or None)
            output_tokens: Output tokens (or None)
            cost: Estimated cost in USD (or None)
            search_results: Search results dict (only for serp_gemini, or None)
            source: Source URL (only for serp_gemini, or None)
            cached: Whether response was from cache
            error_message: Error message if status is "error"
        
        Returns:
            Standardized response dictionary:
            {
                "service": str,
                "status": "success" | "error",
                "prompt": str,
                "response": str or None,
                "model": str or None,
                "metadata": {
                    "response_time_ms": int or None,
                    "tokens_used": int or None,
                    "input_tokens": int or None,
                    "output_tokens": int or None,
                    "cost": float or None,
                    "search_results": dict or None,
                    "source": str or None,
                    "cached": bool
                },
                "error": str or None,
                "timestamp": str (ISO format)
            }
        """
        return {
            "service": service_name,
            "status": status,
            "prompt": prompt,
            "response": response_text if status == "success" else None,
            "model": model,
            "metadata": {
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "search_results": search_results,
                "source": source,
                "cached": cached
            },
            "error": error_message if status == "error" else None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


def success_response(
    data: Any,
    message: str = "Request successful",
    status_code: int = 200,
    metadata: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create a standardized success response
    
    Args:
        data: The response data (can be dict, list, or any JSON-serializable type)
        message: Human-readable success message
        status_code: HTTP status code (default 200)
        metadata: Optional metadata dictionary
    
    Returns:
        tuple: (response_dict, status_code)
    """
    response = {
        "status": "success",
        "status_code": status_code,
        "message": message,
        "metadata": metadata or {},
        "data": data
    }
    
    # Add timestamp to metadata if not present
    if "timestamp" not in response["metadata"]:
        response["metadata"]["timestamp"] = datetime.utcnow().isoformat() + "Z"
    
    return response, status_code


def error_response(
    error: str,
    message: str = "Request failed",
    status_code: int = 400,
    metadata: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create a standardized error response
    
    Args:
        error: Error description or error message
        message: Human-readable error message
        status_code: HTTP status code (default 400)
        metadata: Optional metadata dictionary
    
    Returns:
        tuple: (response_dict, status_code)
    """
    response = {
        "status": "error",
        "status_code": status_code,
        "message": message,
        "metadata": metadata or {},
        "error": error,
        "data": None
    }
    
    # Add timestamp to metadata if not present
    if "timestamp" not in response["metadata"]:
        response["metadata"]["timestamp"] = datetime.utcnow().isoformat() + "Z"
    
    return response, status_code
