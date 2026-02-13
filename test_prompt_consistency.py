"""
Test Prompt Consistency
Compare outputs when running the same prompt multiple times
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
TEST_QUERY = "best project management tools 2024"
BRAND_DOMAINS = ["asana.com", "trello.com"]
NUM_TESTS = 3  # Run same prompt 3 times

def test_endpoint_consistency(endpoint: str, service_name: str):
    """
    Test if endpoint gives consistent results for same prompt
    
    Args:
        endpoint: API endpoint to test
        service_name: Name of service (gemini-only, claude-only, etc.)
    """
    print("\n" + "="*80)
    print(f"🧪 TESTING: {service_name}")
    print("="*80)
    print(f"Query: {TEST_QUERY}")
    print(f"Running {NUM_TESTS} times...\n")
    
    results = []
    
    # Run same prompt multiple times
    for i in range(NUM_TESTS):
        print(f"Run {i+1}/{NUM_TESTS}...")
        
        try:
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                json={
                    "query": TEST_QUERY,
                    "brand_domains": BRAND_DOMAINS
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                results.append({
                    'run': i+1,
                    'status': data.get('status'),
                    'snapshot_id': data.get('snapshot_id'),
                    'metrics': data.get('metrics', {}),
                    'execution_time': data.get('execution_time_ms'),
                    'debug': data.get('debug', {})
                })
                print(f"  ✅ Success (snapshot_id: {data.get('snapshot_id')})")
            else:
                print(f"  ❌ Failed: {response.status_code}")
                results.append({'run': i+1, 'status': 'error', 'error': response.text})
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({'run': i+1, 'status': 'exception', 'error': str(e)})
        
        # Wait between calls
        if i < NUM_TESTS - 1:
            time.sleep(2)
    
    # Analyze results
    print("\n" + "-"*80)
    print("📊 COMPARISON ANALYSIS")
    print("-"*80)
    
    if len(results) < 2:
        print("❌ Not enough successful runs to compare")
        return
    
    # Compare citations count
    print("\n1️⃣ Citations Count:")
    for r in results:
        if r.get('status') == 'success':
            citations = r.get('debug', {}).get('citations_count', 0)
            print(f"   Run {r['run']}: {citations} citations")
    
    # Compare metrics
    print("\n2️⃣ Metrics Comparison:")
    metrics_keys = ['visibility_score', 'intensity_score', 'total_citations', 'brand_mentioned']
    
    for key in metrics_keys:
        print(f"\n   {key}:")
        values = []
        for r in results:
            if r.get('status') == 'success':
                value = r.get('metrics', {}).get(key, 'N/A')
                values.append(value)
                print(f"      Run {r['run']}: {value}")
        
        # Check if all values are same
        if values and len(set(str(v) for v in values)) == 1:
            print(f"      ✅ CONSISTENT (all same)")
        else:
            print(f"      ⚠️ DIFFERENT (varies between runs)")
    
    # Compare execution time
    print("\n3️⃣ Execution Time:")
    for r in results:
        if r.get('status') == 'success':
            time_ms = r.get('execution_time', 0)
            print(f"   Run {r['run']}: {time_ms}ms")
    
    # Get detailed citations from debug
    print("\n4️⃣ Citations Detail (URLs):")
    for r in results:
        if r.get('status') == 'success':
            print(f"\n   Run {r['run']}:")
            raw_response = r.get('debug', {}).get('gemini_raw_response', '') or r.get('debug', {}).get('claude_raw_response', '')
            
            # Try to parse citations from raw response
            try:
                if raw_response:
                    # Extract JSON from response
                    import re
                    json_match = re.search(r'(\{[\s\S]*\})', raw_response)
                    if json_match:
                        parsed = json.loads(json_match.group(1))
                        citations = parsed.get('citations', [])
                        
                        for idx, cit in enumerate(citations[:3]):  # Show first 3
                            url = cit.get('url', 'N/A')
                            title = cit.get('title', 'N/A')[:50]
                            print(f"      [{idx+1}] {url}")
                            print(f"          {title}...")
            except:
                print(f"      ⚠️ Could not parse citations")
    
    print("\n" + "="*80)
    print("🔍 CONCLUSION:")
    print("="*80)
    print("AI outputs are typically DIFFERENT each time because:")
    print("  • AI models use temperature/randomness")
    print("  • Different citations may be selected")
    print("  • Text variations are normal")
    print("  • Metrics may vary slightly")
    print("\n✅ This is EXPECTED behavior for AI systems")
    print("="*80)


def main():
    print("\n" + "="*80)
    print("🧪 PROMPT CONSISTENCY TEST")
    print("="*80)
    print("This test checks if the same prompt produces consistent outputs")
    print("across multiple runs.\n")
    
    # Test Gemini-only
    test_endpoint_consistency(
        endpoint="/api/tracking/gemini-only",
        service_name="Gemini-Only"
    )
    
    print("\n\n")
    
    # Test Claude-only
    test_endpoint_consistency(
        endpoint="/api/tracking/claude-only",
        service_name="Claude-Only"
    )
    
    print("\n" + "="*80)
    print("✅ TESTING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
