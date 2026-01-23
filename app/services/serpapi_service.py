import requests
from typing import Any, Dict, Optional


class SerpApiService:
    """Service for extracting Google Answer Boxes via SerpApi"""
    
    def __init__(self):
        self.api_key = None
        self.endpoint = None
    
    def initialize(self, api_key: str, endpoint: str):
        """Initialize the SerpApi service with API key and endpoint"""
        self.api_key = api_key
        self.endpoint = endpoint
    
    def fetch_google_search(
        self, 
        query: str, 
        gl: str = "us", 
        hl: str = "en", 
        google_domain: str = "google.com"
    ) -> Dict[str, Any]:
        """
        Fetch Google search results from SerpApi
        
        Args:
            query: Search query string
            gl: Country code (e.g., 'us', 'lk', 'uk')
            hl: Language code (e.g., 'en', 'es')
            google_domain: Google domain to search (e.g., 'google.com', 'google.lk')
        
        Returns:
            Dict containing full SerpApi response
            
        Raises:
            RuntimeError: If API key is not configured
            requests.RequestException: If API request fails
        """
        if not self.api_key:
            raise RuntimeError("SerpApi API key not configured")
        
        params = {
            "engine": "google",
            "q": query,
            "gl": gl,
            "hl": hl,
            "google_domain": google_domain,
            "api_key": self.api_key,
        }
        
        response = requests.get(self.endpoint, params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    
    def extract_answer_box(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Google's answer box or featured snippet from SerpApi response
        
        Args:
            data: Full SerpApi response data
        
        Returns:
            Normalized dict with answer box information, or None if not found
            Structure: {
                'kind': 'answer_box' or 'featured_snippet',
                'type': type of answer box (if available),
                'title': title text,
                'answer': main answer text,
                'snippet': snippet text,
                'source': source URL,
                'displayed_link': displayed link text,
                'raw': original raw data
            }
        """
        # 1) Direct answer box (calculator, weather, currency, sports, etc.)
        answer_box = data.get("answer_box")
        if isinstance(answer_box, dict):
            return {
                "kind": "answer_box",
                "type": answer_box.get("type"),
                "title": answer_box.get("title"),
                "answer": answer_box.get("answer") or answer_box.get("result") or answer_box.get("snippet"),
                "snippet": answer_box.get("snippet"),
                "source": answer_box.get("source") or answer_box.get("link"),
                "displayed_link": answer_box.get("displayed_link"),
                "raw": answer_box,
            }
        
        # 2) Featured snippet (position 0 style snippet)
        featured = data.get("featured_snippet")
        if isinstance(featured, dict):
            return {
                "kind": "featured_snippet",
                "title": featured.get("title"),
                "answer": featured.get("snippet") or featured.get("answer"),
                "source": featured.get("link"),
                "displayed_link": featured.get("displayed_link"),
                "raw": featured,
            }
        
        return None
    
    def extract_organic_results(self, data: Dict[str, Any], limit: Optional[int] = None) -> list:
        """
        Extract traditional organic search results (blue links) from Google
        
        Args:
            data: Full SerpApi response data
            limit: Optional limit on number of results to return (e.g., top 10)
        
        Returns:
            List of organic results with structure:
            [{
                'position': int,
                'title': str,
                'link': str,
                'displayed_link': str,
                'snippet': str,
                'date': str (optional),
                'sitelinks': list (optional),
                'rich_snippet': dict (optional)
            }]
        """
        organic_results = data.get("organic_results", [])
        
        if not isinstance(organic_results, list):
            return []
        
        results = []
        for item in organic_results:
            if not isinstance(item, dict):
                continue
                
            result = {
                "position": item.get("position"),
                "title": item.get("title"),
                "link": item.get("link"),
                "displayed_link": item.get("displayed_link"),
                "snippet": item.get("snippet"),
                "date": item.get("date"),
                "sitelinks": item.get("sitelinks", {}).get("inline") if item.get("sitelinks") else None,
                "rich_snippet": item.get("rich_snippet")
            }
            
            results.append(result)
            
            if limit and len(results) >= limit:
                break
        
        return results
    
    # ==================== NEW METHODS ====================
    
    def detect_and_extract_features(self, data: Dict[str, Any], limit_organic: Optional[int] = 10) -> Dict[str, Any]:
        """
        Detect and extract all Google search features:
        - Knowledge Graph
        - Answer Box
        - AI Overview
        - Organic Results
        
        Args:
            data: Full SerpApi response data
            limit_organic: Optional limit for organic results (default: 10)
        
        Returns:
            Dict with structure:
            {
                "detection": [1, 0, 1, 1],  # [knowledge_graph, answer_box, ai_overview, organic_results]
                "knowledge_graph": {...} or None,
                "answer_box": {...} or None,
                "ai_overview": {...} or None,
                "organic_results": [...] or []
            }
        """
        # Extract each feature
        knowledge_graph = self.extract_knowledge_graph(data)
        answer_box = self.extract_answer_box_full(data)
        ai_overview = self.extract_ai_overview(data)
        organic_results = self.extract_organic_results(data, limit=limit_organic)
        
        # Create detection array [1=exists, 0=doesn't exist]
        detection = [
            1 if knowledge_graph else 0,
            1 if answer_box else 0,
            1 if ai_overview else 0,
            1 if organic_results else 0
        ]
        
        return {
            "detection": detection,
            "knowledge_graph": knowledge_graph,
            "answer_box": answer_box,
            "ai_overview": ai_overview,
            "organic_results": organic_results,
            "organic_results_count": len(organic_results)
        }
    
    def extract_knowledge_graph(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Knowledge Graph (info panel on right side of Google results)
        
        Args:
            data: Full SerpApi response data
        
        Returns:
            Dict with knowledge graph data or None if not found
            Structure: {
                'exists': True,
                'title': str,
                'type': str,
                'description': str,
                'source': {'name': str, 'link': str},
                'image': str,
                'attributes': dict,  # Dynamic fields like 'born', 'founded', etc.
                'profiles': [{'name': str, 'link': str}],
                'people_also_search_for': [{'name': str, 'link': str, 'image': str}]
            }
        """
        kg = data.get("knowledge_graph")
        if not isinstance(kg, dict):
            return None
        
        # Extract source information
        source = None
        if kg.get("source"):
            source = {
                "name": kg["source"].get("name"),
                "link": kg["source"].get("link")
            }
        
        # Extract dynamic attributes (born, founded, CEO, etc.)
        # Exclude standard fields to get entity-specific attributes
        standard_fields = {
            'title', 'type', 'description', 'source', 'image', 
            'profiles', 'people_also_search_for', 'see_results_about'
        }
        attributes = {k: v for k, v in kg.items() if k not in standard_fields}
        
        # Extract social profiles
        profiles = []
        if kg.get("profiles"):
            for profile in kg["profiles"]:
                if isinstance(profile, dict):
                    profiles.append({
                        "name": profile.get("name"),
                        "link": profile.get("link")
                    })
        
        # Extract related searches
        related = []
        if kg.get("people_also_search_for"):
            for item in kg["people_also_search_for"]:
                if isinstance(item, dict):
                    related.append({
                        "name": item.get("name"),
                        "link": item.get("link"),
                        "image": item.get("image")
                    })
        
        return {
            "exists": True,
            "title": kg.get("title"),
            "type": kg.get("type"),
            "description": kg.get("description"),
            "source": source,
            "image": kg.get("image"),
            "attributes": attributes,
            "profiles": profiles if profiles else None,
            "people_also_search_for": related if related else None
        }
    
    def extract_answer_box_full(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract Answer Box / Featured Snippet (complete version with all fields)
        
        Args:
            data: Full SerpApi response data
        
        Returns:
            Dict with answer box data or None if not found
            Structure: {
                'exists': True,
                'kind': 'answer_box' or 'featured_snippet',
                'type': str,
                'title': str,
                'snippet': str,
                'answer': str,
                'list': [str],  # For list-type answers
                'table': [[str]],  # For table-type answers
                'link': str,
                'displayed_link': str
            }
        """
        # Check for answer_box first
        answer_box = data.get("answer_box")
        if isinstance(answer_box, dict):
            return {
                "exists": True,
                "kind": "answer_box",
                "type": answer_box.get("type"),
                "title": answer_box.get("title"),
                "snippet": answer_box.get("snippet"),
                "answer": answer_box.get("answer") or answer_box.get("result"),
                "list": answer_box.get("list"),
                "table": answer_box.get("table"),
                "link": answer_box.get("link") or answer_box.get("source"),
                "displayed_link": answer_box.get("displayed_link")
            }
        
        # Check for featured_snippet
        featured = data.get("featured_snippet")
        if isinstance(featured, dict):
            return {
                "exists": True,
                "kind": "featured_snippet",
                "type": featured.get("type"),
                "title": featured.get("title"),
                "snippet": featured.get("snippet"),
                "answer": featured.get("snippet"),
                "list": featured.get("list"),
                "table": featured.get("table"),
                "link": featured.get("link"),
                "displayed_link": featured.get("displayed_link")
            }
        
        return None
    
    def extract_ai_overview(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract AI Overview (Google's AI-generated summary)
        
        Args:
            data: Full SerpApi response data
        
        Returns:
            Dict with AI overview data or None if not found
            Structure: {
                'exists': True,
                'text': str,  # Full AI-generated text
                'sources': [...]  # Cited sources
                'page_token': str  # Token for fetching full content
            }
        """
        ai_overview = data.get("ai_overview")
        if not isinstance(ai_overview, dict):
            return None
        
        # AI Overview requires a second API call using page_token or serpapi_link
        page_token = ai_overview.get("page_token")
        serpapi_link = ai_overview.get("serpapi_link")
        
        # If we have a page_token, fetch the full AI Overview content
        full_content = None
        if page_token and self.api_key:
            try:
                full_content = self._fetch_ai_overview_content(page_token)
                
                # Check if AI Overview is actually empty
                if full_content:
                    search_info = full_content.get("search_information", {})
                    ai_state = search_info.get("ai_overview_state", "")
                    
                    # If Google says AI Overview is empty, return None
                    if "empty" in ai_state.lower() or full_content.get("error"):
                        return None
                        
            except Exception as e:
                # If fetching fails, just log and continue
                print(f"Warning: Failed to fetch AI Overview content: {e}")
                return None
        
        # Extract data from full content if available
        text = None
        sources = []
        text_blocks = []
        
        if full_content:
            # Extract AI Overview data
            ai_overview_data = full_content.get("ai_overview", {})
            
            # Extract text blocks and combine into full text
            text_blocks_raw = ai_overview_data.get("text_blocks", [])
            text_parts = []
            
            for block in text_blocks_raw:
                if isinstance(block, dict):
                    snippet = block.get("snippet", "")
                    block_type = block.get("type", "")
                    list_items = block.get("list", [])
                    
                    if snippet:
                        # Add formatting based on type
                        if block_type == "heading":
                            text_parts.append(f"\n{snippet}\n")
                        elif block_type == "paragraph":
                            text_parts.append(snippet)
                    
                    # Handle list items
                    if list_items:
                        for item in list_items:
                            if isinstance(item, dict):
                                item_snippet = item.get("snippet", "")
                                if item_snippet:
                                    text_parts.append(f"• {item_snippet}")
                                
                                # Handle nested lists
                                nested_list = item.get("list", [])
                                for nested_item in nested_list:
                                    if isinstance(nested_item, dict):
                                        nested_snippet = nested_item.get("snippet", "")
                                        if nested_snippet:
                                            text_parts.append(f"  - {nested_snippet}")
                    
                    text_blocks.append(block)
            
            # Combine all text parts
            if text_parts:
                text = "\n".join(text_parts)
            
            # Extract references/sources
            references = ai_overview_data.get("references", [])
            for ref in references:
                if isinstance(ref, dict):
                    sources.append({
                        "title": ref.get("title"),
                        "link": ref.get("link"),
                        "snippet": ref.get("snippet"),
                        "source": ref.get("source"),
                        "index": ref.get("index")
                    })
        
        return {
            "exists": True,
            "text": text,
            "sources": sources if sources else None,
            "text_blocks": text_blocks if text_blocks else None,  # Include raw text blocks for debugging
            "page_token": page_token,
            "serpapi_link": serpapi_link
        }
    
    def _fetch_ai_overview_content(self, page_token: str) -> Dict[str, Any]:
        """
        Fetch full AI Overview content using page_token
        
        Args:
            page_token: Token from initial search response
        
        Returns:
            Dict containing full AI Overview data
        """
        params = {
            "engine": "google_ai_overview",
            "page_token": page_token,
            "api_key": self.api_key,
        }
        
        response = requests.get(self.endpoint, params=params, timeout=60)
        response.raise_for_status()
        return response.json()


# Create a singleton instance
serpapi_service = SerpApiService()
