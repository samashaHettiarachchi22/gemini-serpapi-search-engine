"""
Answer Box Only Test - Simplified Version
"""
import requests
import json

print("=" * 60)
print("ANSWER BOX TEST")
print("=" * 60)

# Test queries that usually have answer boxes
test_queries = [
    {"query": "2+2", "gl": "us", "desc": "Calculator"},
    {"query": "weather in new york", "gl": "us", "desc": "Weather"},
    {"query": "1 usd to eur", "gl": "us", "desc": "Currency"},
]

try:
    for test in test_queries:
        print(f"\n Testing: {test['desc']} - '{test['query']}'")
        
        response = requests.post(
            "http://127.0.0.1:5000/api/serpapi/answer-box",
            json={"query": test['query'], "gl": test['gl']},
            timeout=30
        )
        
        data = response.json()
        
        if data.get("found"):
            print(f"    Answer: {data['data'].get('answer', 'N/A')}")
        else:
            print(f"    No answer box")
    
    print("\n" + "=" * 60)
    print(" Done!")
    
except requests.exceptions.ConnectionError:
    print("\n Server not running! Start with: python run.py")
except Exception as e:
    print(f"\n Error: {e}")