"""
SerpApi Example Client
Demonstrates how to use the SerpApi endpoints to track answer engine results
"""

import requests
import json
from typing import Dict, Any

# Base URL - update this if your server is running on a different port
BASE_URL = "http://localhost:5000"


def print_json(data: Dict[str, Any]):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def test_answer_box(query: str, gl: str = "us", hl: str = "en"):
    """
    Test the answer box endpoint
    
    Args:
        query: Search query
        gl: Country code (e.g., 'us', 'lk', 'uk')
        hl: Language code (e.g., 'en', 'es')
    """
    print(f"\n{'='*60}")
    print(f"Testing Answer Box for: {query}")
    print(f"Country: {gl}, Language: {hl}")
    print(f"{'='*60}\n")
    
    response = requests.post(
        f"{BASE_URL}/api/serpapi/answer-box",
        json={
            "query": query,
            "gl": gl,
            "hl": hl
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("found"):
            print("✅ Answer Box Found!")
            print(f"\nKind: {data['data'].get('kind')}")
            print(f"Title: {data['data'].get('title')}")
            print(f"Answer: {data['data'].get('answer')}")
            print(f"Source: {data['data'].get('source')}")
        else:
            print("❌ No answer box found")
    else:
        print(f"Error: {response.status_code}")
        print_json(response.json())


def test_top_half(query: str, gl: str = "us", hl: str = "en"):
    """
    Test the top-half endpoint (comprehensive answer engine tracking)
    
    Args:
        query: Search query
        gl: Country code
        hl: Language code
    """
    print(f"\n{'='*60}")
    print(f"Testing Top Half Results for: {query}")
    print(f"Country: {gl}, Language: {hl}")
    print(f"{'='*60}\n")
    
    response = requests.post(
        f"{BASE_URL}/api/serpapi/top-half",
        json={
            "query": query,
            "gl": gl,
            "hl": hl
        }
    )
    
    if response.status_code == 200:
        data = response.json()["data"]
        
        # Answer Box
        if data.get("answer_box"):
            print("✅ Answer Box Present")
            print(f"   Kind: {data['answer_box'].get('kind')}")
            print(f"   Answer: {data['answer_box'].get('answer', 'N/A')[:100]}...")
        else:
            print("❌ No Answer Box")
        
        # Knowledge Graph
        if data.get("knowledge_graph"):
            print("\n✅ Knowledge Graph Present")
            print(f"   Title: {data['knowledge_graph'].get('title')}")
            print(f"   Type: {data['knowledge_graph'].get('type')}")
        else:
            print("\n❌ No Knowledge Graph")
        
        # People Also Ask
        paa = data.get("people_also_ask", [])
        if paa:
            print(f"\n✅ People Also Ask: {len(paa)} questions")
            for i, q in enumerate(paa[:3], 1):
                print(f"   {i}. {q.get('question')}")
        else:
            print("\n❌ No People Also Ask")
        
        # Top Organic Results
        organic = data.get("organic_results", [])
        if organic:
            print(f"\n📊 Top {len(organic)} Organic Results:")
            for result in organic:
                print(f"   {result.get('position')}. {result.get('title')}")
        
        # Summary
        print(f"\n📈 Summary:")
        print(f"   Has Answer Engine Result: {data.get('has_answer_engine_result')}")
        
    else:
        print(f"Error: {response.status_code}")
        print_json(response.json())


def test_people_also_ask(query: str, gl: str = "us"):
    """
    Test the People Also Ask endpoint
    
    Args:
        query: Search query
        gl: Country code
    """
    print(f"\n{'='*60}")
    print(f"Testing People Also Ask for: {query}")
    print(f"{'='*60}\n")
    
    response = requests.post(
        f"{BASE_URL}/api/serpapi/people-also-ask",
        json={
            "query": query,
            "gl": gl
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        count = data.get("count", 0)
        
        if count > 0:
            print(f"✅ Found {count} PAA questions:\n")
            for i, paa in enumerate(data["data"], 1):
                print(f"{i}. {paa.get('question')}")
                print(f"   Source: {paa.get('displayed_link', 'N/A')}")
                print()
        else:
            print("❌ No PAA questions found")
    else:
        print(f"Error: {response.status_code}")
        print_json(response.json())


def test_knowledge_graph(query: str, gl: str = "us"):
    """
    Test the knowledge graph endpoint
    
    Args:
        query: Search query
        gl: Country code
    """
    print(f"\n{'='*60}")
    print(f"Testing Knowledge Graph for: {query}")
    print(f"{'='*60}\n")
    
    response = requests.post(
        f"{BASE_URL}/api/serpapi/knowledge-graph",
        json={
            "query": query,
            "gl": gl
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get("found"):
            kg = data["data"]
            print("✅ Knowledge Graph Found!")
            print(f"\nTitle: {kg.get('title')}")
            print(f"Type: {kg.get('type')}")
            print(f"Description: {kg.get('description', 'N/A')[:200]}...")
            print(f"Website: {kg.get('website', 'N/A')}")
        else:
            print("❌ No knowledge graph found")
    else:
        print(f"Error: {response.status_code}")
        print_json(response.json())


def main():
    """Run example tests"""
    print("\n" + "="*60)
    print("SerpApi Answer Engine Tracking - Example Client")
    print("="*60)
    
    # Example 1: Simple factual query (likely has answer box)
    test_answer_box("what is the capital of sri lanka", gl="lk", hl="en")
    
    # Example 2: Comprehensive top-half tracking
    test_top_half("python programming language", gl="us", hl="en")
    
    # Example 3: People Also Ask
    test_people_also_ask("how to learn python", gl="us")
    
    # Example 4: Knowledge Graph (entity query)
    test_knowledge_graph("elon musk", gl="us")
    
    print("\n" + "="*60)
    print("Examples Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the server.")
        print("Make sure the Flask app is running on http://localhost:5000")
        print("Run: python run.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
