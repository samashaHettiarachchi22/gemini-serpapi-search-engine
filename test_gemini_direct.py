"""
Test Gemini Model Directly
Run same prompt multiple times to compare outputs
"""

from google import genai
import os
from dotenv import load_dotenv
import json

# Load environment
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = 'models/gemini-2.5-flash'
TEST_QUERY = "best project management tools 2024"

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


def test_gemini_consistency(num_tests=3):
    """
    Test Gemini with same prompt multiple times
    
    Args:
        num_tests: Number of times to run same prompt
    """
    print("\n" + "="*80)
    print("🧪 TESTING GEMINI MODEL DIRECTLY")
    print("="*80)
    print(f"Model: {GEMINI_MODEL}")
    print(f"Query: {TEST_QUERY}")
    print(f"Running {num_tests} times with SAME prompt...\n")
    
    # Initialize Gemini client
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    results = []
    
    # Run same prompt multiple times
    for i in range(num_tests):
        print(f"\n{'='*80}")
        print(f"RUN {i+1}/{num_tests}")
        print('='*80)
        
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=PROMPT
            )
            
            response_text = response.text
            
            # Try to parse JSON
            import re
            json_match = re.search(r'(\{[\s\S]*\})', response_text)
            
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                    
                    # Extract key info
                    citations = parsed.get('citations', [])
                    ai_overview = parsed.get('ai_overview', {})
                    
                    print(f"\n✅ Success - Parsed JSON")
                    print(f"   Citations: {len(citations)}")
                    print(f"   AI Overview: {ai_overview.get('text', '')[:100]}...")
                    
                    # Show first 3 citations
                    print(f"\n   First 3 Citations:")
                    for idx, cit in enumerate(citations[:3], 1):
                        print(f"      [{idx}] {cit.get('url', 'N/A')}")
                        print(f"          Title: {cit.get('title', 'N/A')[:60]}...")
                    
                    results.append({
                        'run': i+1,
                        'success': True,
                        'citations': citations,
                        'citation_count': len(citations),
                        'ai_overview': ai_overview.get('text', ''),
                        'parsed': parsed
                    })
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON Parse Error: {e}")
                    print(f"   Raw response: {response_text[:200]}...")
                    results.append({'run': i+1, 'success': False, 'error': str(e)})
            else:
                print(f"❌ No JSON found in response")
                print(f"   Raw response: {response_text[:200]}...")
                results.append({'run': i+1, 'success': False, 'error': 'No JSON'})
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({'run': i+1, 'success': False, 'error': str(e)})
    
    # Compare results
    print("\n\n" + "="*80)
    print("📊 COMPARISON ANALYSIS")
    print("="*80)
    
    successful_runs = [r for r in results if r.get('success')]
    
    if len(successful_runs) < 2:
        print("❌ Not enough successful runs to compare")
        return
    
    # Compare citation counts
    print("\n1️⃣ Citation Count Comparison:")
    citation_counts = [r['citation_count'] for r in successful_runs]
    for r in successful_runs:
        print(f"   Run {r['run']}: {r['citation_count']} citations")
    
    if len(set(citation_counts)) == 1:
        print(f"   ✅ CONSISTENT - All runs have {citation_counts[0]} citations")
    else:
        print(f"   ⚠️ DIFFERENT - Citation counts vary: {citation_counts}")
    
    # Compare citation URLs
    print("\n2️⃣ Citation URLs Comparison:")
    for r in successful_runs:
        print(f"\n   Run {r['run']}:")
        for idx, cit in enumerate(r['citations'][:3], 1):
            print(f"      [{idx}] {cit.get('url', 'N/A')}")
    
    # Check if URLs are same across runs
    if len(successful_runs) >= 2:
        urls_run1 = [c.get('url') for c in successful_runs[0]['citations']]
        urls_run2 = [c.get('url') for c in successful_runs[1]['citations']]
        
        if urls_run1 == urls_run2:
            print("\n   ✅ IDENTICAL - All citation URLs are the same")
        else:
            print("\n   ⚠️ DIFFERENT - Citation URLs vary between runs")
    
    # Compare AI Overview text
    print("\n3️⃣ AI Overview Text Comparison:")
    for r in successful_runs:
        print(f"\n   Run {r['run']}: {r['ai_overview'][:150]}...")
    
    if len(successful_runs) >= 2:
        if successful_runs[0]['ai_overview'] == successful_runs[1]['ai_overview']:
            print("\n   ✅ IDENTICAL - AI overview text is the same")
        else:
            print("\n   ⚠️ DIFFERENT - AI overview text varies")
    
    print("\n\n" + "="*80)
    print("🔍 CONCLUSION:")
    print("="*80)
    print("Gemini outputs typically vary because:")
    print("  • AI uses temperature/sampling (randomness)")
    print("  • Different text generation each time")
    print("  • Citations may be reordered or changed")
    print("  • Content remains similar but not identical")
    print("\n✅ This is EXPECTED behavior for AI models")
    print("="*80)


if __name__ == "__main__":
    test_gemini_consistency(num_tests=3)
