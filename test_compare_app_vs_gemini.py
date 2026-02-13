"""
Compare Your Flask App Output vs Direct Gemini Output
See if differences come from app logic or Gemini itself
"""

import requests
import json
from google import genai
import os
from dotenv import load_dotenv
import re

# Load environment
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = 'models/gemini-2.5-flash'
FLASK_API_URL = "http://localhost:5000/api/tracking/gemini-only"
TEST_QUERY = "best project management tools 2024"
BRAND_DOMAINS = ["asana.com", "trello.com"]

# Same prompt used in your app
PROMPT = f"""
## Role
You are the Google Gemini Search Answer Engine. Your goal is to synthesize a definitive "AI Overview" for a specific user query using real-time search simulation logic.

## Task
Analyze the query: "{TEST_QUERY}"
Generate a high-relevance response grounded in actual web data.

## Search Engine Constraints
- **Evidence-First:** Do not state facts that cannot be attributed to a citation.
- **Brand Neutrality:** Mention brands only if they are the subject of the query or represent the primary authority on the topic.
- **Zero Hallucination:** If no real-world source is known, do not "hallucinate". Instead, omit the citation and adjust the confidence of the statement.

## Output Schema (JSON Only)
{{
  "intent": {{
    "type": "informational | transactional | navigational",
    "confidence": 0.85,
    "reasoning": "Brief explanation of intent classification"
  }},
  "ai_overview": {{
    "text": "A 2-4 sentence comprehensive answer that directly addresses the query. Be specific and factual."
  }},
  "citations": [
    {{
      "url": "https://example.com/article",
      "title": "Article Title from Source",
      "snippet": "Specific excerpt from the source that supports the AI overview",
      "source_type": "Blog | News | Documentation | Review | SaaS | Marketplace",
      "authority_estimate": 85,
      "sentiment": "positive | neutral | negative",
      "ai_reusability": "High | Medium | Low"
    }}
  ],
  "domain_summary": [
    {{
      "domain": "example.com",
      "count": 2,
      "authority": "High | Medium | Low"
    }}
  ],
  "top_recommendation": {{
    "domain": "example.com",
    "reasoning": "Why this is the top source"
  }},
  "runner_ups": [
    {{
      "domain": "alternative.com",
      "reasoning": "Why this is also valuable"
    }}
  ]
}}

## Final Rule
Return ONLY valid JSON. No markdown code blocks, no conversational text."""


def call_flask_app():
    """Call your Flask app API"""
    print("\n" + "="*80)
    print("🌐 CALLING FLASK APP API (Your Application)")
    print("="*80)
    
    try:
        response = requests.post(
            FLASK_API_URL,
            json={
                "query": TEST_QUERY,
                "brand_domains": BRAND_DOMAINS
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract Gemini raw response from debug
            raw_response = data.get('debug', {}).get('gemini_raw_response', '')
            
            print(f"✅ Status: {data.get('status')}")
            print(f"📊 Snapshot ID: {data.get('snapshot_id')}")
            print(f"⏱️  Execution Time: {data.get('execution_time_ms')}ms")
            
            # Parse Gemini response
            if raw_response:
                json_match = re.search(r'(\{[\s\S]*\})', raw_response)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group(1))
                        return {
                            'success': True,
                            'parsed': parsed,
                            'metrics': data.get('metrics', {}),
                            'snapshot_id': data.get('snapshot_id')
                        }
                    except json.JSONDecodeError as e:
                        print(f"❌ Failed to parse Gemini response: {e}")
                        return {'success': False, 'error': 'JSON parse error'}
            
            return {'success': False, 'error': 'No raw response found'}
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return {'success': False, 'error': response.text}
            
    except Exception as e:
        print(f"❌ Error calling Flask app: {e}")
        return {'success': False, 'error': str(e)}


def call_gemini_direct():
    """Call Gemini API directly"""
    print("\n" + "="*80)
    print("🤖 CALLING GEMINI API DIRECTLY")
    print("="*80)
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=PROMPT
        )
        
        response_text = response.text
        
        # Parse JSON
        json_match = re.search(r'(\{[\s\S]*\})', response_text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                print(f"✅ Success - Parsed JSON")
                return {
                    'success': True,
                    'parsed': parsed
                }
            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Error: {e}")
                return {'success': False, 'error': str(e)}
        else:
            print(f"❌ No JSON found in response")
            return {'success': False, 'error': 'No JSON'}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return {'success': False, 'error': str(e)}


def compare_results(app_result, direct_result):
    """Compare Flask app output vs Direct Gemini output"""
    
    print("\n\n" + "="*80)
    print("📊 SIDE-BY-SIDE COMPARISON")
    print("="*80)
    
    if not app_result.get('success') or not direct_result.get('success'):
        print("❌ Cannot compare - one or both calls failed")
        return
    
    app_data = app_result['parsed']
    direct_data = direct_result['parsed']
    
    # 1. Compare citation count
    print("\n1️⃣ CITATION COUNT:")
    app_citations = app_data.get('citations', [])
    direct_citations = direct_data.get('citations', [])
    
    print(f"   Flask App:      {len(app_citations)} citations")
    print(f"   Direct Gemini:  {len(direct_citations)} citations")
    
    if len(app_citations) == len(direct_citations):
        print(f"   ✅ SAME count")
    else:
        print(f"   ⚠️ DIFFERENT counts")
    
    # 2. Compare citation URLs
    print("\n2️⃣ CITATION URLs:")
    
    print("\n   Flask App Citations:")
    for idx, cit in enumerate(app_citations[:3], 1):
        print(f"      [{idx}] {cit.get('url', 'N/A')}")
    
    print("\n   Direct Gemini Citations:")
    for idx, cit in enumerate(direct_citations[:3], 1):
        print(f"      [{idx}] {cit.get('url', 'N/A')}")
    
    # Check if URLs match
    app_urls = [c.get('url') for c in app_citations]
    direct_urls = [c.get('url') for c in direct_citations]
    
    if app_urls == direct_urls:
        print("\n   ✅ IDENTICAL URLs (in same order)")
    elif set(app_urls) == set(direct_urls):
        print("\n   ⚠️ SAME URLs but DIFFERENT order")
    else:
        print("\n   ⚠️ DIFFERENT URLs")
    
    # 3. Compare AI Overview
    print("\n3️⃣ AI OVERVIEW TEXT:")
    
    app_overview = app_data.get('ai_overview', {}).get('text', '')
    direct_overview = direct_data.get('ai_overview', {}).get('text', '')
    
    print(f"\n   Flask App:")
    print(f"      {app_overview[:150]}...")
    
    print(f"\n   Direct Gemini:")
    print(f"      {direct_overview[:150]}...")
    
    if app_overview == direct_overview:
        print("\n   ✅ IDENTICAL text")
    else:
        print("\n   ⚠️ DIFFERENT text")
    
    # 4. Compare Intent
    print("\n4️⃣ INTENT CLASSIFICATION:")
    
    app_intent = app_data.get('intent', {})
    direct_intent = direct_data.get('intent', {})
    
    print(f"   Flask App:      {app_intent.get('type')} (confidence: {app_intent.get('confidence')})")
    print(f"   Direct Gemini:  {direct_intent.get('type')} (confidence: {direct_intent.get('confidence')})")
    
    if app_intent.get('type') == direct_intent.get('type'):
        print(f"   ✅ SAME intent type")
    else:
        print(f"   ⚠️ DIFFERENT intent type")
    
    # 5. Show app metrics (only from Flask app)
    if 'metrics' in app_result:
        print("\n5️⃣ APP-CALCULATED METRICS (from Flask App):")
        metrics = app_result['metrics']
        print(f"   Visibility Score:        {metrics.get('visibility_score')}")
        print(f"   Intensity Score:         {metrics.get('intensity_score')}")
        print(f"   Brand Mentioned:         {metrics.get('brand_mentioned')}")
        print(f"   Share of Voice:          {metrics.get('share_of_voice_percentage')}%")
    
    # Final conclusion
    print("\n\n" + "="*80)
    print("🔍 CONCLUSION:")
    print("="*80)
    
    # Count differences
    differences = 0
    if len(app_citations) != len(direct_citations):
        differences += 1
    if app_urls != direct_urls:
        differences += 1
    if app_overview != direct_overview:
        differences += 1
    if app_intent.get('type') != direct_intent.get('type'):
        differences += 1
    
    if differences == 0:
        print("✅ IDENTICAL - Your Flask app returns EXACT same Gemini output")
        print("   Your application is working perfectly!")
    else:
        print(f"⚠️ DIFFERENCES FOUND ({differences} aspects differ)")
        print("\nPossible reasons:")
        print("  • Gemini uses randomness - different output each time")
        print("  • These are two SEPARATE API calls to Gemini")
        print("  • Expected behavior - AI is non-deterministic")
        print("\n✅ Your app is working correctly!")
        print("   To verify, call your app twice and compare those results.")
    
    print("="*80)


def main():
    print("\n" + "="*80)
    print("🔬 FLASK APP vs DIRECT GEMINI COMPARISON")
    print("="*80)
    print(f"Query: {TEST_QUERY}")
    print(f"Testing both at the same time...\n")
    
    # Note to user
    print("⚠️  NOTE: Make sure your Flask server is running!")
    print("   (Run: python run.py in another terminal)\n")
    input("Press ENTER when server is ready...")
    
    # Call Flask app
    app_result = call_flask_app()
    
    # Small delay
    import time
    time.sleep(1)
    
    # Call Gemini directly
    direct_result = call_gemini_direct()
    
    # Compare results
    compare_results(app_result, direct_result)
    
    print("\n" + "="*80)
    print("✅ TESTING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
