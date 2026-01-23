"""Quick test of SerpApi answer box endpoint"""
import requests
import json

try:
    print("Testing Answer Box Endpoint...")
    print("Query: 'what is the capital of sri lanka'")
    print("-" * 50)
    
    response = requests.post(
        "http://127.0.0.1:5000/api/serpapi/answer-box",
        json={
            "query": "what is the capital of sri lanka",
            "gl": "lk",
            "hl": "en"
        },
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print("\nResponse:")
    print(json.dumps(response.json(), indent=2))
    
except Exception as e:
    print(f"Error: {e}")
