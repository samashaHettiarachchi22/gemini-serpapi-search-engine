"""
Response formatter utility for consistent API responses
"""
from datetime import datetime
from typing import Any, Dict, Optional


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
