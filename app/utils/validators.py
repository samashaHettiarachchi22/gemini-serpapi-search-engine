"""
Validation utilities for request data
"""

def validate_prompt(data):
    """
    Validate prompt data from request
    
    Args:
        data (dict): Request JSON data
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not data:
        return False, "No data provided"
    
    if 'prompt' not in data:
        return False, "Missing 'prompt' field"
    
    if not isinstance(data['prompt'], str):
        return False, "'prompt' must be a string"
    
    if not data['prompt'].strip():
        return False, "'prompt' cannot be empty"
    
    return True, None
