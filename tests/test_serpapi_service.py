"""
Unit tests for SerpApi service
"""
import pytest
from unittest.mock import Mock, patch
from app.services.serpapi_service import SerpApiService


@pytest.fixture
def serpapi_service():
    """Create a fresh SerpApiService instance for testing"""
    service = SerpApiService()
    service.initialize("test_api_key", "https://serpapi.com/search.json")
    return service


def test_service_initialization():
    """Test service initialization"""
    service = SerpApiService()
    assert service.api_key is None
    assert service.endpoint is None
    
    service.initialize("test_key", "test_endpoint")
    assert service.api_key == "test_key"
    assert service.endpoint == "test_endpoint"


def test_extract_answer_box_direct():
    """Test extracting a direct answer box"""
    service = SerpApiService()
    
    mock_data = {
        "answer_box": {
            "type": "calculator_result",
            "title": "Calculator Result",
            "answer": "4",
            "result": "4"
        }
    }
    
    result = service.extract_answer_box(mock_data)
    
    assert result is not None
    assert result["kind"] == "answer_box"
    assert result["type"] == "calculator_result"
    assert result["answer"] == "4"


def test_extract_answer_box_featured_snippet():
    """Test extracting a featured snippet"""
    service = SerpApiService()
    
    mock_data = {
        "featured_snippet": {
            "title": "Python Programming",
            "snippet": "Python is a high-level programming language",
            "link": "https://example.com"
        }
    }
    
    result = service.extract_answer_box(mock_data)
    
    assert result is not None
    assert result["kind"] == "featured_snippet"
    assert result["title"] == "Python Programming"
    assert result["answer"] == "Python is a high-level programming language"
    assert result["source"] == "https://example.com"


def test_extract_answer_box_none():
    """Test when no answer box is present"""
    service = SerpApiService()
    
    mock_data = {
        "organic_results": []
    }
    
    result = service.extract_answer_box(mock_data)
    
    assert result is None


@patch('requests.get')
def test_fetch_google_search(mock_get, serpapi_service):
    """Test fetching Google search results"""
    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = {"search_results": "test"}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    result = serpapi_service.fetch_google_search("test query", gl="us", hl="en")
    
    # Verify the request was made with correct parameters
    mock_get.assert_called_once()
    call_args = mock_get.call_args
    
    assert call_args[1]['params']['q'] == "test query"
    assert call_args[1]['params']['gl'] == "us"
    assert call_args[1]['params']['hl'] == "en"
    assert call_args[1]['params']['api_key'] == "test_api_key"
    
    assert result == {"search_results": "test"}


def test_fetch_google_search_no_api_key():
    """Test that fetching without API key raises error"""
    service = SerpApiService()
    
    with pytest.raises(RuntimeError, match="SerpApi API key not configured"):
        service.fetch_google_search("test query")
