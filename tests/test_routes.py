import pytest
from app import create_app

@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    yield app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'

def test_home_endpoint(client):
    """Test home endpoint"""
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data
    assert 'endpoints' in data


# SerpApi Tests
def test_answer_box_endpoint_missing_query(client):
    """Test answer box endpoint without query parameter"""
    response = client.post('/api/serpapi/answer-box', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'query' in data['error'].lower()


def test_answer_box_endpoint_with_query(client):
    """Test answer box endpoint with valid query"""
    # Note: This requires a valid SERPAPI_API_KEY in environment
    response = client.post('/api/serpapi/answer-box', json={
        'query': '2+2',
        'gl': 'us'
    })
    
    # Should return 200 even if no answer box found
    assert response.status_code == 200
    data = response.get_json()
    assert 'success' in data
    assert 'found' in data
    assert 'query' in data
