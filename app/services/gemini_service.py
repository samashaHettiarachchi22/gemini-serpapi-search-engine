from google import genai
from flask import current_app
from app.utils.response_formatter import StandardServiceResponse

class GeminiService:
    """Service for interacting with Google Gemini AI"""
    
    def __init__(self):
        self.client = None
    
    def initialize(self, api_key):
        """Initialize the Gemini client with API key"""
        self.client = genai.Client(api_key=api_key)
    
    def list_models(self):
        """
        List all available Gemini models
        
        Returns:
            list: List of model names
        """
        if not self.client:
            raise ValueError("Gemini client not initialized")
        
        models = self.client.models.list()
        return [model.name for model in models]
    
    def generate_content(self, prompt, model=None, log_to_db=True):
        """
        Generate content using Gemini AI
        
        Args:
            prompt (str): The prompt to generate content from
            model (str, optional): The model to use. Defaults to config value.
            log_to_db (bool): Whether to log to database. Defaults to True.
        
        Returns:
            str: Generated text response
        """
        import time
        if not self.client:
            raise ValueError("Gemini client not initialized")
        
        if model is None:
            model = current_app.config.get('GEMINI_MODEL', 'models/gemini-2.5-flash')
        
        start_time = time.time()
        
        # Configuration for consistent outputs
        from google.genai import types
        generation_config = types.GenerateContentConfig(
            temperature=0.0,  # 0 = deterministic, 1 = creative (default ~0.7)
            top_p=1.0,        # Nucleus sampling
            top_k=1           # Consider only top token
        )
        
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=generation_config
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        
        response_text = response.text
        
        # Estimate tokens (Gemini doesn't return usage)
        def estimate_tokens(text):
            return len(text or "") // 4
        
        input_tokens = estimate_tokens(prompt)
        output_tokens = estimate_tokens(response_text)
        total_tokens = input_tokens + output_tokens
        
        # Estimate cost (Gemini Flash: $0.10 per 1M tokens)
        estimated_cost = (total_tokens / 1_000_000) * 0.10
        
        # Log to database for persistence
        if log_to_db:
            try:
                from app.models.optimized_tracking import search_tracking_db_optimized
                
                print(f"🔵 Attempting to log Gemini API call to database...")
                log_id = search_tracking_db_optimized.log_api_call(
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
                print(f"✅ Database log saved successfully (ID: {log_id})")
            except Exception as db_err:
                # Don't fail request if database logging fails
                import traceback
                print(f"❌ Database logging failed for Gemini: {db_err}")
                print(f"📋 Full error:\n{traceback.format_exc()}")
        
        # Return standardized response format
        return StandardServiceResponse.format_service_response(
            service_name="gemini",
            prompt=prompt,
            response_text=response_text,
            status="success",
            model=model,
            response_time_ms=response_time_ms,
            tokens_used=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=estimated_cost,
            search_results=None,
            source=None,
            cached=False
        )

# Singleton instance
gemini_service = GeminiService()
