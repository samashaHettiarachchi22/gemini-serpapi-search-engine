"""
Simple SerpApi Test - Run this AFTER starting the server
"""
import time

print("=" * 60)
print("SERPAPI TEST - Make sure server is running first!")
print("=" * 60)
print("\nWaiting 2 seconds for you to start the server...")
print("(If server is already running, this will just proceed)")
time.sleep(2)

print("\n" + "-" * 60)
print("Testing: What is the capital of Sri Lanka?")
print("-" * 60)

try:
    import requests
    import json
    
    response = requests.post(
        "http://127.0.0.1:5000/api/serpapi/answer-box",
        json={
            "query": "what is the capital of sri lanka",
            "gl": "lk",
            "hl": "en"
        },
        timeout=30
    )
    
    print(f"\n✓ Server Response: {response.status_code}")
    
    data = response.json()
    
    if data.get("success"):
        if data.get("found"):
            print("\n" + "=" * 60)
            print("✓ SUCCESS! Answer Box Found!")
            print("=" * 60)
            answer_data = data['data']
            print(f"\nKind: {answer_data.get('kind')}")
            print(f"Answer: {answer_data.get('answer')}")
            print(f"Source: {answer_data.get('source')}")
        else:
            print("\n✓ Server works but no answer box found for this query")
    else:
        print(f"\n✗ Error from server: {data.get('error')}")
    
    print("\n" + "=" * 60)
    print("Full Response:")
    print("=" * 60)
    print(json.dumps(data, indent=2))
    
except requests.exceptions.ConnectionError:
    print("\n✗ ERROR: Cannot connect to server!")
    print("\nPlease start the server first:")
    print("1. Open a terminal")
    print("2. Run: python run.py")
    print("3. Wait for 'Running on http://127.0.0.1:5000'")
    print("4. Then run this test again")
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")

print("\n" + "=" * 60)
