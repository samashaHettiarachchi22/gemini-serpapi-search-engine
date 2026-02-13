import requests
import time
from typing import Optional, Dict, Any
from app.utils.cache_manager import cache_manager
from app.utils.rate_limiter import rate_limiter
from app.utils.cost_tracker import cost_tracker
from app.utils.optimization_config import OptimizationConfig
from app.utils.response_formatter import StandardServiceResponse

class ClaudeService:
    """Optimized service for interacting with Claude (Anthropic) API"""
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.api_url: str = "https://api.anthropic.com/v1/messages"
        self.model: str = "claude-3-5-sonnet-20241022"
        self.max_tokens: int = 500  # Reduced default for cost optimization
    
    def initialize(self, api_key: str, api_url: Optional[str] = None):
        """Initialize Claude service with API key"""
        if not api_key:
            raise ValueError("Claude API key is required")
        self.api_key = api_key
        if api_url:
            self.api_url = api_url
    
    def _truncate_prompt(self, prompt: str) -> str:
        """Truncate prompt to save tokens"""
        if len(prompt) > OptimizationConfig.MAX_PROMPT_LENGTH:
            return prompt[:OptimizationConfig.MAX_PROMPT_LENGTH] + "..."
        return prompt
    
    def generate_content(self, prompt: str, model: Optional[str] = None, max_tokens: Optional[int] = None, use_cache: bool = True) -> Dict[str, Any]:
        """
        Generate content using Claude API with optimization
        
        Args:
            prompt: The prompt to send to Claude
            model: Optional model name
            max_tokens: Optional max tokens
            use_cache: Whether to use cache (default: True)
            
        Returns:
            Dictionary with response text and metadata
        """
        if not self.api_key:
            raise ValueError("Claude service not initialized. Call initialize() first.")
        
        # Optimize prompt length
        optimized_prompt = self._truncate_prompt(prompt)
        
        # Check cache first
        if use_cache:
            cached_response = cache_manager.get('claude', optimized_prompt, model=model)
            if cached_response:
                # Mark cached response
                if isinstance(cached_response, dict) and 'metadata' in cached_response:
                    cached_response['metadata']['cached'] = True
                return cached_response
        
        # Rate limiting
        rate_limiter.wait_if_needed('claude')
        
        # Determine model (use cheaper if configured)
        selected_model = model or OptimizationConfig.get_model_for_service('claude')
        selected_max_tokens = max_tokens or min(self.max_tokens, OptimizationConfig.MAX_RESPONSE_TOKENS)
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": selected_model,
            "max_tokens": selected_max_tokens,
            "temperature": 0.0,  # 0 = deterministic, 1 = creative
            "messages": [
                {
                    "role": "user",
                    "content": optimized_prompt
                }
            ]
        }
        
        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(OptimizationConfig.MAX_RETRIES):
            try:
                start_time = time.time()
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                
                result = response.json()
                response_time_ms = int((time.time() - start_time) * 1000)
                
                # Extract text from response
                if "content" in result and len(result["content"]) > 0:
                    response_text = result["content"][0]["text"]
                    
                    # Record rate limit
                    rate_limiter.record_call('claude')
                    
                    # Track costs (in-memory for real-time stats)
                    usage = result.get("usage", {})
                    total_tokens = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
                    cost_tracker.record_api_call('claude', optimized_prompt, response_text, total_tokens)
                    
                    # Also save to database for persistence
                    try:
                        from app.models.optimized_tracking import search_tracking_db_optimized
                        
                        # Calculate cost
                        input_tokens = usage.get('input_tokens', 0)
                        output_tokens = usage.get('output_tokens', 0)
                        cost = cost_tracker._calculate_claude_cost(input_tokens, output_tokens)
                        
                        print(f"🔵 Attempting to log Claude API call to database...")
                        log_id = search_tracking_db_optimized.log_api_call(
                            service='claude',
                            prompt=optimized_prompt,
                            model=selected_model,
                            response=response_text,
                            response_time_ms=response_time_ms,
                            success=True,
                            max_tokens=selected_max_tokens,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            total_tokens=total_tokens,
                            estimated_cost=cost
                        )
                        print(f"✅ Database log saved successfully (ID: {log_id})")
                    except Exception as db_err:
                        # Don't fail the request if database logging fails
                        import traceback
                        print(f"❌ Database logging failed: {db_err}")
                        print(f"📋 Full error:\n{traceback.format_exc()}")
                    
                    # Return standardized response format
                    response_data = StandardServiceResponse.format_service_response(
                        service_name="claude",
                        prompt=optimized_prompt,
                        response_text=response_text,
                        status="success",
                        model=result.get("model", selected_model),
                        response_time_ms=response_time_ms,
                        tokens_used=total_tokens,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost=cost,
                        search_results=None,
                        source=None,
                        cached=False
                    )
                    
                    # Cache the response
                    if use_cache:
                        cache_manager.set('claude', optimized_prompt, response_data, model=model)
                    
                    return response_data
                else:
                    raise ValueError("Unexpected response format from Claude API")
                    
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < OptimizationConfig.MAX_RETRIES - 1:
                    wait_time = OptimizationConfig.RETRY_DELAY_SECONDS * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
        
        # Return error in standard format if all retries failed
        return StandardServiceResponse.format_service_response(
            service_name="claude",
            prompt=optimized_prompt,
            response_text="",
            status="error",
            model=selected_model,
            error_message=f"Claude API request failed after {OptimizationConfig.MAX_RETRIES} retries: {str(last_error)}"
        )
    
    def list_available_models(self) -> list:
        """
        Return list of available Claude models
        Note: Anthropic doesn't have a list models endpoint, so we return known models
        """
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]

# Create singleton instance
claude_service = ClaudeService()
