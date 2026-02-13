"""
Optimization Configuration
Cost and performance settings
"""

class OptimizationConfig:
    """Configuration for cost and performance optimization"""
    
    # API Call Optimization
    ENABLE_CACHING = True
    CACHE_TTL_SECONDS = 3600  # 1 hour
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2
    
    # Token Optimization
    MAX_PROMPT_LENGTH = 2000  # Characters
    MAX_RESPONSE_TOKENS = 500  # Tokens per API call
    BATCH_SIZE = 10  # Items to process in one batch
    
    # Rate Limiting
    RATE_LIMIT_CALLS_PER_MINUTE = 60
    RATE_LIMIT_ENABLED = True
    
    # Parallel Processing
    MAX_CONCURRENT_REQUESTS = 5
    ENABLE_PARALLEL_PROCESSING = True
    
    # Database Optimization
    DB_BATCH_INSERT_SIZE = 100
    DB_CONNECTION_POOL_SIZE = 10
    DB_CONNECTION_POOL_RECYCLE = 3600
    
    # Cost Tracking
    GEMINI_COST_PER_1K_TOKENS = 0.0001  # USD
    CLAUDE_COST_PER_1K_TOKENS = 0.0003  # USD
    TRACK_COSTS = True
    
    # Performance Monitoring
    LOG_SLOW_QUERIES = True
    SLOW_QUERY_THRESHOLD_MS = 1000
    
    # Feature Flags
    SKIP_LOW_PRIORITY_ANALYSIS = False  # Skip non-critical analysis if needed
    USE_CHEAPER_MODELS = False  # Use cheaper AI models
    
    @classmethod
    def get_model_for_service(cls, service: str) -> str:
        """Get optimal model based on cost settings"""
        if cls.USE_CHEAPER_MODELS:
            return {
                'gemini': 'models/gemini-1.5-flash',
                'claude': 'claude-3-haiku-20240307'
            }.get(service, 'default')
        else:
            return {
                'gemini': 'models/gemini-2.5-flash',
                'claude': 'claude-3-5-sonnet-20241022'
            }.get(service, 'default')
