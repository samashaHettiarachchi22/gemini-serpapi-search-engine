"""
Combined SerpAPI + Gemini Service
Handles Google searches via SerpAPI and processes results with Gemini AI
"""
import requests
from typing import Any, Dict, Optional, List
from google import genai
from flask import current_app
from app.utils.response_formatter import StandardServiceResponse


class SerpGeminiService:
    """Combined service for SerpAPI search + Gemini AI processing"""
    
    def __init__(self):
        # SerpAPI configuration
        self.serpapi_key: Optional[str] = None
        self.serpapi_endpoint: str = "https://serpapi.com/search"
        
        # Gemini configuration
        self.gemini_client = None
    
    def initialize(self, serpapi_key: str, gemini_key: str, serpapi_endpoint: Optional[str] = None):
        """
        Initialize the combined service
        
        Args:
            serpapi_key: SerpAPI API key
            gemini_key: Google Gemini API key
            serpapi_endpoint: Optional custom SerpAPI endpoint
        """
        if not serpapi_key:
            raise ValueError("SerpAPI key is required")
        if not gemini_key:
            raise ValueError("Gemini API key is required")
            
        self.serpapi_key = serpapi_key
        if serpapi_endpoint:
            self.serpapi_endpoint = serpapi_endpoint
            
        # Initialize Gemini client
        self.gemini_client = genai.Client(api_key=gemini_key)
    
    # ==================== SERPAPI METHODS ====================
    
    def search_google(
        self,
        query: str,
        gl: str = "us",
        hl: str = "en",
        google_domain: str = "google.com",
        log_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch Google search results from SerpApi
        
        Args:
            query: Search query string
            gl: Country code (e.g., 'us', 'lk', 'uk')
            hl: Language code (e.g., 'en', 'es')
            google_domain: Google domain to search
            log_to_db: Whether to log to database
        
        Returns:
            Dict containing full SerpApi response
        """
        import time
        
        if not self.serpapi_key:
            raise RuntimeError("SerpApi not initialized")
        
        params = {
            "engine": "google",
            "q": query,
            "gl": gl,
            "hl": hl,
            "google_domain": google_domain,
            "api_key": self.serpapi_key,
        }
        
        start_time = time.time()
        response = requests.get(self.serpapi_endpoint, params=params, timeout=60)
        response.raise_for_status()
        response_time_ms = int((time.time() - start_time) * 1000)
        
        result = response.json()
        
        # Log to database
        if log_to_db:
            try:
                from app.models.optimized_tracking import search_tracking_db_optimized
                
                serpapi_cost_per_call = 0.002  # $0.002 per search
                response_summary = f"Results: {len(result.get('organic_results', []))} organic"
                
                search_tracking_db_optimized.log_api_call(
                    service='serpapi',
                    prompt=query,
                    model='google_search',
                    response=response_summary,
                    response_time_ms=response_time_ms,
                    success=True,
                    estimated_cost=serpapi_cost_per_call
                )
            except Exception as db_err:
                print(f"❌ Database logging failed for SerpAPI: {db_err}")
        
        return result
    
    def extract_answer_box(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract Google's answer box or featured snippet"""
        # Try answer_box first
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
            }
        
        # Try featured_snippet
        featured = data.get("featured_snippet")
        if isinstance(featured, dict):
            return {
                "kind": "featured_snippet",
                "title": featured.get("title"),
                "answer": featured.get("snippet") or featured.get("answer"),
                "source": featured.get("link"),
                "displayed_link": featured.get("displayed_link"),
            }
        
        return None
    
    def extract_knowledge_graph(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract Knowledge Graph information"""
        kg = data.get("knowledge_graph")
        if not isinstance(kg, dict):
            return None
        
        return {
            "title": kg.get("title"),
            "type": kg.get("type"),
            "description": kg.get("description"),
            "image": kg.get("image"),
            "source": kg.get("source"),
        }
    
    def extract_organic_results(self, data: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """Extract organic search results"""
        organic_results = data.get("organic_results", [])
        
        results = []
        for item in organic_results[:limit]:
            if isinstance(item, dict):
                results.append({
                    "position": item.get("position"),
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                })
        
        return results
    
    def detect_and_extract_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect and extract all Google search features
        
        Returns:
            Dict with detection array and extracted features
        """
        knowledge_graph = self.extract_knowledge_graph(data)
        answer_box = self.extract_answer_box(data)
        organic_results = self.extract_organic_results(data)
        
        detection = [
            1 if knowledge_graph else 0,
            1 if answer_box else 0,
            0,  # ai_overview placeholder
            1 if organic_results else 0
        ]
        
        return {
            "detection": detection,
            "knowledge_graph": knowledge_graph,
            "answer_box": answer_box,
            "organic_results": organic_results,
        }
    
    # ==================== GEMINI METHODS ====================
    
    def process_with_gemini(
        self,
        prompt: str,
        model: Optional[str] = None,
        log_to_db: bool = True
    ) -> str:
        """
        Process content using Gemini AI
        
        Args:
            prompt: The prompt to send to Gemini
            model: Optional model name
            log_to_db: Whether to log to database
        
        Returns:
            str: Generated text response
        """
        import time
        
        if not self.gemini_client:
            raise ValueError("Gemini not initialized")
        
        if model is None:
            model = current_app.config.get('GEMINI_MODEL', 'models/gemini-2.5-flash')
        
        start_time = time.time()
        
        # Configuration for consistent outputs
        from google.genai import types
        generation_config = types.GenerateContentConfig(
            temperature=0.0,
            top_p=1.0,
            top_k=1
        )
        
        response = self.gemini_client.models.generate_content(
            model=model,
            contents=prompt,
            config=generation_config
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        
        response_text = response.text
        
        # Estimate tokens and cost
        def estimate_tokens(text):
            return len(text or "") // 4
        
        input_tokens = estimate_tokens(prompt)
        output_tokens = estimate_tokens(response_text)
        total_tokens = input_tokens + output_tokens
        estimated_cost = (total_tokens / 1_000_000) * 0.10
        
        # Log to database
        if log_to_db:
            try:
                from app.models.optimized_tracking import search_tracking_db_optimized
                
                search_tracking_db_optimized.log_api_call(
                    service='gemini',
                    prompt=prompt,
                    model=model,
                    response=response_text,
                    response_time_ms=response_time_ms,
                    success=True,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=estimated_cost
                )
            except Exception as db_err:
                print(f"❌ Database logging failed for Gemini: {db_err}")
        
        # Return as dict with metadata (not standard format yet, for internal use)
        return {
            "text": response_text,
            "tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": estimated_cost,
            "response_time_ms": response_time_ms
        }
    
    # ==================== COMBINED WORKFLOWS ====================
    
    def search_and_process(
        self,
        query: str,
        processing_prompt: Optional[str] = None,
        gl: str = "us",
        hl: str = "en",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow: Search Google → Extract features → Process with Gemini
        Returns standardized response format
        
        Args:
            query: Search query
            processing_prompt: Optional custom prompt for Gemini (uses answer box if None)
            gl: Country code
            hl: Language code
            model: Optional Gemini model name
        
        Returns:
            Standardized response format
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: Search Google
            search_results = self.search_google(query, gl=gl, hl=hl, log_to_db=True)
            
            # Step 2: Extract features
            features = self.detect_and_extract_features(search_results)
            
            # Step 3: Process with Gemini
            gemini_data = None
            gemini_response_text = ""
            total_tokens = 0
            gemini_cost = 0
            
            if processing_prompt:
                gemini_data = self.process_with_gemini(processing_prompt, model=model, log_to_db=True)
            elif features.get("answer_box"):
                # Use answer box content for Gemini processing
                answer_text = features["answer_box"].get("answer", "")
                if answer_text:
                    prompt = f"Summarize and explain: {answer_text}"
                    gemini_data = self.process_with_gemini(prompt, model=model, log_to_db=True)
            
            # Extract Gemini response details
            if gemini_data:
                gemini_response_text = gemini_data.get("text", "")
                total_tokens = gemini_data.get("tokens", 0)
                gemini_cost = gemini_data.get("cost", 0)
            
            # Calculate total cost (SerpAPI + Gemini)
            serpapi_cost = 0.002
            total_cost = serpapi_cost + gemini_cost
            
            # Get source from answer box or first organic result
            source = None
            if features.get("answer_box"):
                source = features["answer_box"].get("source")
            elif features.get("organic_results") and len(features["organic_results"]) > 0:
                source = features["organic_results"][0].get("link")
            
            total_time_ms = int((time.time() - start_time) * 1000)
            
            # Return standardized response format
            return StandardServiceResponse.format_service_response(
                service_name="serp_gemini",
                prompt=query,
                response_text=gemini_response_text,
                status="success",
                model=model or current_app.config.get('GEMINI_MODEL', 'models/gemini-2.5-flash'),
                response_time_ms=total_time_ms,
                tokens_used=total_tokens,
                input_tokens=gemini_data.get("input_tokens") if gemini_data else None,
                output_tokens=gemini_data.get("output_tokens") if gemini_data else None,
                cost=total_cost,
                search_results=features,
                source=source,
                cached=False
            )
            
        except Exception as e:
            # Return error in standard format
            return StandardServiceResponse.format_service_response(
                service_name="serp_gemini",
                prompt=query,
                response_text="",
                status="error",
                model=model,
                error_message=str(e)
            )


# Singleton instance
serp_gemini_service = SerpGeminiService()
