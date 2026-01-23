import pytest
from app.services.gemini_service import GeminiService

def test_gemini_service_initialization():
    """Test Gemini service can be initialized"""
    service = GeminiService()
    assert service.client is None
    
def test_gemini_service_requires_initialization():
    """Test Gemini service requires initialization before use"""
    service = GeminiService()
    with pytest.raises(ValueError):
        service.list_models()
