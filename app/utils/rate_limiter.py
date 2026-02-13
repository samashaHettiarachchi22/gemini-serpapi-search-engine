"""
Rate Limiter to prevent API quota exhaustion
"""

import time
from collections import deque
from typing import Dict
from app.utils.optimization_config import OptimizationConfig


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self):
        self._calls: Dict[str, deque] = {}
    
    def _clean_old_calls(self, service: str):
        """Remove calls older than 1 minute"""
        if service not in self._calls:
            self._calls[service] = deque()
            return
        
        current_time = time.time()
        while self._calls[service] and current_time - self._calls[service][0] > 60:
            self._calls[service].popleft()
    
    def can_make_call(self, service: str) -> bool:
        """
        Check if we can make an API call
        
        Args:
            service: Service name (gemini, claude, serpapi)
            
        Returns:
            True if call is allowed
        """
        if not OptimizationConfig.RATE_LIMIT_ENABLED:
            return True
        
        self._clean_old_calls(service)
        
        if service not in self._calls:
            return True
        
        return len(self._calls[service]) < OptimizationConfig.RATE_LIMIT_CALLS_PER_MINUTE
    
    def wait_if_needed(self, service: str):
        """
        Wait if rate limit is reached
        
        Args:
            service: Service name
        """
        if not OptimizationConfig.RATE_LIMIT_ENABLED:
            return
        
        while not self.can_make_call(service):
            time.sleep(0.5)  # Wait 500ms
    
    def record_call(self, service: str):
        """
        Record an API call
        
        Args:
            service: Service name
        """
        if not OptimizationConfig.RATE_LIMIT_ENABLED:
            return
        
        if service not in self._calls:
            self._calls[service] = deque()
        
        self._calls[service].append(time.time())
    
    def get_stats(self, service: str) -> Dict[str, int]:
        """Get rate limit statistics for a service"""
        self._clean_old_calls(service)
        
        current_calls = len(self._calls.get(service, []))
        remaining = OptimizationConfig.RATE_LIMIT_CALLS_PER_MINUTE - current_calls
        
        return {
            'calls_last_minute': current_calls,
            'remaining_calls': max(0, remaining),
            'limit': OptimizationConfig.RATE_LIMIT_CALLS_PER_MINUTE
        }


# Global rate limiter instance
rate_limiter = RateLimiter()
