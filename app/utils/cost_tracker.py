"""
Cost Tracker for API usage
Monitor and optimize AI API costs
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from app.utils.optimization_config import OptimizationConfig


class CostTracker:
    """Track API costs in real-time"""
    
    def __init__(self):
        self.costs: Dict[str, list] = {
            'gemini': [],
            'claude': [],
            'serpapi': []
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)"""
        return len(text) // 4
    
    def record_api_call(self, 
                       service: str,
                       prompt: str,
                       response: str = "",
                       actual_tokens: int = None):
        """
        Record an API call with cost
        
        Args:
            service: Service name
            prompt: Input prompt
            response: Output response
            actual_tokens: Actual tokens used (if available)
        """
        if not OptimizationConfig.TRACK_COSTS:
            return
        
        # Calculate tokens
        if actual_tokens:
            total_tokens = actual_tokens
        else:
            input_tokens = self._estimate_tokens(prompt)
            output_tokens = self._estimate_tokens(response)
            total_tokens = input_tokens + output_tokens
        
        # Calculate cost
        cost_per_1k = {
            'gemini': OptimizationConfig.GEMINI_COST_PER_1K_TOKENS,
            'claude': OptimizationConfig.CLAUDE_COST_PER_1K_TOKENS,
            'serpapi': 0.002  # Assuming $0.002 per search
        }.get(service, 0)
        
        cost = (total_tokens / 1000) * cost_per_1k
        
        # Record
        self.costs[service].append({
            'timestamp': datetime.utcnow(),
            'tokens': total_tokens,
            'cost_usd': cost
        })
        
        # Keep only last 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        self.costs[service] = [
            c for c in self.costs[service] 
            if c['timestamp'] > cutoff
        ]
    
    def get_stats(self, service: str = None, hours: int = 24) -> Dict[str, Any]:
        """
        Get cost statistics
        
        Args:
            service: Specific service or None for all
            hours: Time period in hours
            
        Returns:
            Cost statistics
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        if service:
            services = [service]
        else:
            services = ['gemini', 'claude', 'serpapi']
        
        total_cost = 0
        total_calls = 0
        total_tokens = 0
        
        breakdown = {}
        
        for svc in services:
            recent_calls = [
                c for c in self.costs.get(svc, [])
                if c['timestamp'] > cutoff
            ]
            
            svc_cost = sum(c['cost_usd'] for c in recent_calls)
            svc_calls = len(recent_calls)
            svc_tokens = sum(c['tokens'] for c in recent_calls)
            
            breakdown[svc] = {
                'calls': svc_calls,
                'tokens': svc_tokens,
                'cost_usd': round(svc_cost, 4),
                'avg_cost_per_call': round(svc_cost / svc_calls, 4) if svc_calls > 0 else 0
            }
            
            total_cost += svc_cost
            total_calls += svc_calls
            total_tokens += svc_tokens
        
        return {
            'period_hours': hours,
            'total_calls': total_calls,
            'total_tokens': total_tokens,
            'total_cost_usd': round(total_cost, 4),
            'avg_cost_per_call': round(total_cost / total_calls, 4) if total_calls > 0 else 0,
            'breakdown': breakdown,
            'estimated_monthly_cost': round(total_cost * (30 * 24 / hours), 2)
        }
    
    def get_savings_from_cache(self, cache_hits: int) -> Dict[str, Any]:
        """Calculate savings from cache usage"""
        # Average cost per call
        recent_stats = self.get_stats(hours=24)
        avg_cost = recent_stats.get('avg_cost_per_call', 0)
        
        savings = cache_hits * avg_cost
        
        return {
            'cache_hits': cache_hits,
            'cost_saved_usd': round(savings, 4),
            'estimated_monthly_savings': round(savings * 30, 2)
        }


# Global cost tracker instance
cost_tracker = CostTracker()
