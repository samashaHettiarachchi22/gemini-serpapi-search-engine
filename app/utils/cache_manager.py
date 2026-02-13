"""
Cache Manager for API responses
Reduces duplicate API calls and saves costs
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any
from app.utils.optimization_config import OptimizationConfig


class CacheManager:
    """In-memory cache for API responses"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, service: str, prompt: str, **kwargs) -> str:
        """Generate unique cache key"""
        data = f"{service}:{prompt}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def get(self, service: str, prompt: str, **kwargs) -> Optional[Any]:
        """
        Get cached response
        
        Args:
            service: Service name (gemini, claude)
            prompt: Prompt text
            **kwargs: Additional parameters
            
        Returns:
            Cached response or None
        """
        if not OptimizationConfig.ENABLE_CACHING:
            return None
        
        key = self._generate_key(service, prompt, **kwargs)
        
        if key in self._cache:
            cached_data = self._cache[key]
            
            # Check if cache is still valid
            if time.time() - cached_data['timestamp'] < OptimizationConfig.CACHE_TTL_SECONDS:
                self.hits += 1
                return cached_data['response']
            else:
                # Expired, remove it
                del self._cache[key]
        
        self.misses += 1
        return None
    
    def set(self, service: str, prompt: str, response: Any, **kwargs):
        """
        Cache a response
        
        Args:
            service: Service name
            prompt: Prompt text
            response: Response to cache
            **kwargs: Additional parameters
        """
        if not OptimizationConfig.ENABLE_CACHING:
            return
        
        key = self._generate_key(service, prompt, **kwargs)
        
        self._cache[key] = {
            'response': response,
            'timestamp': time.time()
        }
        
        # Prevent memory overflow - keep only recent 1000 entries
        if len(self._cache) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k]['timestamp']
            )
            for old_key in sorted_keys[:100]:
                del self._cache[old_key]
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate, 2),
            'cached_items': len(self._cache),
            'cache_size_kb': len(str(self._cache)) / 1024
        }


# Global cache instance
cache_manager = CacheManager()
