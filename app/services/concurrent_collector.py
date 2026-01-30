"""
Concurrent Data Collection Service
Runs SerpAPI and Gemini in parallel for efficiency
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import time
from urllib.parse import urlparse

from app.services.serpapi_service import serpapi_service
from app.services.gemini_service import GeminiService
from app.utils.logging_system import analytics_logger, execution_tracker


class ConcurrentDataCollector:
    """
    Collects all data needed for dashboard in parallel
    Optimized for speed and efficiency
    """
    
    def __init__(self, gemini_service: GeminiService):
        self.serpapi = serpapi_service
        self.gemini = gemini_service
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    def collect_all_data(self, 
                        prompt: str,
                        brand_domains: List[str] = None,
                        gl: str = 'us',
                        hl: str = 'en') -> Dict[str, Any]:
        """
        MAIN METHOD: Collect all data concurrently
        
        Args:
            prompt: User's search query
            brand_domains: List of brand domains to track
            gl: Country code
            hl: Language code
            
        Returns:
            Complete data package ready for storage
        """
        brand_domains = brand_domains or []
        
        analytics_logger.log_info(f"Starting data collection", {'query': prompt})
        
        # Step 1: Fetch SerpAPI data (must be first)
        serpapi_data = self._fetch_serpapi_data(prompt, gl, hl)
        
        # Step 2: Concurrent Gemini analysis
        gemini_data = self._analyze_with_gemini_concurrent(prompt, serpapi_data)
        
        # Step 3: Process and structure data for storage
        structured_data = self._structure_for_storage(
            prompt=prompt,
            serpapi_data=serpapi_data,
            gemini_data=gemini_data,
            brand_domains=brand_domains,
            gl=gl,
            hl=hl
        )
        
        analytics_logger.log_info(f"Data collection completed", {'query': prompt})
        
        return structured_data
    
    @execution_tracker.track_service('serpapi')
    def _fetch_serpapi_data(self, query: str, gl: str, hl: str) -> Dict[str, Any]:
        """Fetch data from SerpAPI""" 
        analytics_logger.log_info(f"Fetching SerpAPI data", {'query': query})
        
        # Fetch search results
        search_results = self.serpapi.fetch_google_search(
            query=query,
            gl=gl,
            hl=hl
        )
        
        # Detect and extract features
        features = self.serpapi.detect_and_extract_features(search_results)
        
        return {
            'raw_response': search_results,
            'features': features
        }
    
    def _analyze_with_gemini_concurrent(self, 
                                       prompt: str, 
                                       serpapi_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run multiple Gemini analyses concurrently
        """
        features = serpapi_data['features']
        
        # Prepare concurrent tasks
        tasks = {
            'intent': (self._analyze_intent, prompt),
            'citation_sentiment': (self._analyze_citation_sentiment, features),
        }
        
        results = {}
        futures = {}
        
        # Submit all tasks
        for task_name, (func, arg) in tasks.items():
            future = self.executor.submit(func, arg)
            futures[future] = task_name
        
        # Collect results as they complete
        for future in as_completed(futures):
            task_name = futures[future]
            try:
                results[task_name] = future.result()
            except Exception as e:
                analytics_logger.log_error(
                    f"Gemini task failed: {task_name}", 
                    error=e,
                    extra={'query': prompt}
                )
                results[task_name] = None
        
        return results
    
    @execution_tracker.track_service('gemini')
    def _analyze_intent(self, query: str) -> Dict[str, Any]:
        """Analyze search intent using Gemini"""
        analytics_logger.log_info(f"Analyzing intent with Gemini", {'query': query})
        
        prompt = f"""Analyze the search intent for this query: "{query}"

Classify the intent as one of:
- informational (seeking information, how-to, explanation)
- transactional (buying, purchasing, finding services)
- navigational (looking for specific website or page)

Respond in JSON format:
{{
    "intent_type": "informational|transactional|navigational",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}
"""
        
        try:
            response = self.gemini.generate_content(prompt)
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                intent_data = json.loads(json_match.group())
                return intent_data
            else:
                # Fallback: simple keyword analysis
                return self._fallback_intent_analysis(query)
                
        except Exception as e:
            analytics_logger.log_warning(
                "Gemini intent analysis failed, using fallback",
                extra={'query': query, 'error': str(e)}
            )
            return self._fallback_intent_analysis(query)
    
    def _fallback_intent_analysis(self, query: str) -> Dict[str, Any]:
        """Fallback intent analysis using keywords"""
        query_lower = query.lower()
        
        # Keyword patterns
        informational_keywords = ['what', 'how', 'why', 'when', 'where', 'explain', 'definition']
        transactional_keywords = ['buy', 'purchase', 'order', 'price', 'cost', 'deal', 'discount']
        navigational_keywords = ['login', 'sign in', 'download', 'official', 'website']
        
        scores = {
            'informational': sum(1 for kw in informational_keywords if kw in query_lower),
            'transactional': sum(1 for kw in transactional_keywords if kw in query_lower),
            'navigational': sum(1 for kw in navigational_keywords if kw in query_lower)
        }
        
        if sum(scores.values()) == 0:
            # Default to informational
            return {
                'intent_type': 'informational',
                'confidence': 0.5,
                'reasoning': 'Default classification'
            }
        
        intent_type = max(scores, key=scores.get)
        confidence = scores[intent_type] / sum(scores.values())
        
        return {
            'intent_type': intent_type,
            'confidence': confidence,
            'reasoning': 'Keyword-based classification'
        }
    
    def _analyze_citation_sentiment(self, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for each citation using Gemini
        Returns list of {url, sentiment, readability}
        """
        ai_overview = features.get('ai_overview', {})
        sources = ai_overview.get('sources', [])
        
        if not sources:
            return []
        
        citation_analysis = []
        
        # For efficiency, analyze in batch (up to 10 citations)
        for source in sources[:10]:
            url = source.get('link', '')
            title = source.get('title', '')
            snippet = source.get('snippet', '')
            
            if not url:
                continue
            
            # Simple sentiment analysis (can be enhanced with Gemini)
            sentiment = self._simple_sentiment_analysis(title, snippet)
            ai_reusability = self._calculate_ai_reusability(snippet, title)
            
            citation_analysis.append({
                'url': url,
                'title': title,
                'snippet': snippet,
                'sentiment': sentiment,
                'ai_reusability': ai_reusability
            })
        
        return citation_analysis
    
    def _simple_sentiment_analysis(self, title: str, snippet: str) -> str:
        """Simple sentiment analysis (can be enhanced with Gemini)"""
        text = f"{title} {snippet}".lower()
        
        positive_words = ['best', 'good', 'great', 'excellent', 'top', 'recommended']
        negative_words = ['bad', 'worst', 'poor', 'avoid', 'warning', 'issue']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _calculate_ai_reusability(self, text: str, title: str = "") -> str:
        """Calculate AI reusability category (High/Medium/Low)"""
        if not text:
            return 'Medium'
        
        combined_text = f"{title} {text}".lower()
        score = 0
        
        # High reusability indicators (+1 each)
        high_indicators = [
            'data', 'research', 'study', 'analysis', 'report', 'guide',
            'tutorial', 'documentation', 'official', 'statistics', 'fact',
            'source', 'evidence', 'peer-reviewed', 'published', 'academic'
        ]
        
        # Low reusability indicators (-1 each)
        low_indicators = [
            'opinion', 'blog', 'review', 'personal', 'ad', 'sponsored',
            'sale', 'buy now', 'limited time', 'subscribe', 'click here'
        ]
        
        # Count indicators
        high_count = sum(1 for word in high_indicators if word in combined_text)
        low_count = sum(1 for word in low_indicators if word in combined_text)
        
        # Calculate final score
        score = high_count - low_count
        
        # Categorize
        if score >= 3:
            return 'High'
        elif score <= -2:
            return 'Low'
        else:
            return 'Medium'
    
    def _structure_for_storage(self,
                              prompt: str,
                              serpapi_data: Dict[str, Any],
                              gemini_data: Dict[str, Any],
                              brand_domains: List[str],
                              gl: str,
                              hl: str) -> Dict[str, Any]:
        """
        Structure all collected data for optimized storage
        
        Returns:
            {
                'snapshot_data': {...},      # For search_snapshots table
                'citations_data': [...],     # For citation_sources table
                'positions_data': [...],     # For organic_positions table
                'log_data': {...}           # For execution_logs table
            }
        """
        features = serpapi_data['features']
        intent = gemini_data.get('intent', {})
        citation_sentiment = gemini_data.get('citation_sentiment', [])
        
        # Calculate metrics
        metrics = self._calculate_all_metrics(features, brand_domains)
        
        # === SNAPSHOT DATA ===
        snapshot_data = {
            'query': prompt,
            'timestamp': datetime.utcnow(),
            'country': gl,
            'language': hl,
            'google_domain': 'google.com',
            
            # Intent (from Gemini)
            'intent_type': intent.get('intent_type', 'informational'),
            'intent_confidence': intent.get('confidence', 0.5),
            
            # Feature flags
            'has_knowledge_graph': metrics['has_knowledge_graph'],
            'has_answer_box': metrics['has_answer_box'],
            'has_ai_overview': metrics['has_ai_overview'],
            'has_featured_snippet': metrics['has_featured_snippet'],
            'has_related_questions': metrics['has_related_questions'],
            
            # AI Answer metrics
            'brand_mentioned': metrics['brand_mentioned'],
            'ai_overview_text': metrics['ai_overview_text'],
            'total_citations': metrics['total_citations'],
            'brand_citations': metrics['brand_citations'],
            
            # Organic metrics
            'total_organic_results': metrics['total_organic_results'],
            'brand_organic_positions': metrics['brand_organic_positions'],
            
            # Calculated scores
            'visibility_score': metrics['visibility_score'],
            'intensity_score': metrics['intensity_score'],
            'share_of_voice_percentage': metrics['share_of_voice_percentage'],
            
            # Metadata
            'processing_time_ms': 0,  # Will be updated
            'created_at': datetime.utcnow()
        }
        
        # === CITATIONS DATA ===
        citations_data = self._prepare_citations_data(
            features, 
            brand_domains, 
            citation_sentiment
        )
        
        # === POSITIONS DATA ===
        positions_data = self._prepare_positions_data(features, brand_domains)
        
        # === LOG DATA ===
        log_data = execution_tracker.get_log_data(prompt)
        
        return {
            'snapshot_data': snapshot_data,
            'citations_data': citations_data,
            'positions_data': positions_data,
            'log_data': log_data
        }
    
    def _calculate_all_metrics(self, 
                               features: Dict[str, Any], 
                               brand_domains: List[str]) -> Dict[str, Any]:
        """Calculate all metrics from features"""
        
        # Feature detection
        has_kg = bool(features.get('knowledge_graph'))
        has_ab = bool(features.get('answer_box'))
        has_ai = bool(features.get('ai_overview'))
        has_fs = bool(features.get('featured_snippet'))
        has_rq = bool(features.get('related_questions'))
        
        # AI Overview analysis
        ai_overview = features.get('ai_overview', {})
        ai_text = ai_overview.get('overview', '')
        sources = ai_overview.get('sources', [])
        
        brand_mentioned = any(
            brand.lower() in ai_text.lower()
            for brand in brand_domains
        )
        
        total_citations = len(sources)
        brand_citations = sum(
            1 for source in sources
            if any(brand.lower() in source.get('link', '').lower() 
                   for brand in brand_domains)
        )
        
        # Organic results analysis
        organic_results = features.get('organic_results', [])
        total_organic = len(organic_results)
        brand_organic = sum(
            1 for result in organic_results
            if any(brand.lower() in result.get('link', '').lower()
                   for brand in brand_domains)
        )
        
        # Calculate scores
        visibility_score = 0
        if has_ai: visibility_score += 40
        if has_ab: visibility_score += 30
        if has_kg: visibility_score += 20
        if has_fs: visibility_score += 25
        if has_rq: visibility_score += 15
        visibility_score = min(visibility_score, 100)
        
        intensity_score = visibility_score  # Same calculation for now
        
        # Share of voice
        if total_organic > 0 or total_citations > 0:
            total_positions = total_organic + total_citations
            brand_positions = brand_organic + brand_citations
            share_of_voice = (brand_positions / total_positions) * 100
        else:
            share_of_voice = 0.0
        
        return {
            'has_knowledge_graph': has_kg,
            'has_answer_box': has_ab,
            'has_ai_overview': has_ai,
            'has_featured_snippet': has_fs,
            'has_related_questions': has_rq,
            'brand_mentioned': brand_mentioned,
            'ai_overview_text': ai_text[:1000] if ai_text else None,  # Limit size
            'total_citations': total_citations,
            'brand_citations': brand_citations,
            'total_organic_results': total_organic,
            'brand_organic_positions': brand_organic,
            'visibility_score': visibility_score,
            'intensity_score': intensity_score,
            'share_of_voice_percentage': round(share_of_voice, 2)
        }
    
    def _prepare_citations_data(self,
                               features: Dict[str, Any],
                               brand_domains: List[str],
                               citation_sentiment: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare citation data for batch insert"""
        ai_overview = features.get('ai_overview', {})
        sources = ai_overview.get('sources', [])
        
        citations_data = []
        
        for idx, source in enumerate(sources):
            url = source.get('link', '')
            if not url:
                continue
            
            domain = urlparse(url).netloc.lower()
            
            # Determine if brand
            is_brand = any(brand.lower() in domain for brand in brand_domains)
            
            # Determine source type
            source_type = self._categorize_source(domain, is_brand)
            
            # Get sentiment from analysis
            sentiment_data = next(
                (s for s in citation_sentiment if s['url'] == url),
                {}
            )
            
            citations_data.append({
                'domain': domain,
                'url': url,
                'title': source.get('title', ''),
                'source_type': source_type,
                'is_brand': is_brand,
                'authority_score': self._get_authority_score(domain),
                'sentiment': sentiment_data.get('sentiment', 'neutral'),
                'ai_reusability_score': sentiment_data.get('ai_reusability', 'Medium'),
                'citation_index': idx,
                'timestamp': datetime.utcnow()
            })
        
        return citations_data
    
    def _prepare_positions_data(self,
                               features: Dict[str, Any],
                               brand_domains: List[str]) -> List[Dict[str, Any]]:
        """Prepare organic positions data for batch insert"""
        organic_results = features.get('organic_results', [])
        positions_data = []
        
        for idx, result in enumerate(organic_results[:10], 1):
            url = result.get('link', '')
            if not url:
                continue
            
            domain = urlparse(url).netloc.lower()
            is_brand = any(brand.lower() in domain for brand in brand_domains)
            
            positions_data.append({
                'position': idx,
                'domain': domain,
                'url': url,
                'is_brand': is_brand,
                'timestamp': datetime.utcnow()
            })
        
        return positions_data
    
    def _categorize_source(self, domain: str, is_brand: bool) -> str:
        """Categorize source type"""
        if is_brand:
            return 'owned'
        elif any(tld in domain for tld in ['.gov', '.edu']):
            return 'authority'
        elif 'wikipedia' in domain:
            return 'authority'
        else:
            return 'neutral'
    
    def _get_authority_score(self, domain: str) -> float:
        """Get authority score for domain (can be cached)"""
        # High authority domains
        authority_domains = {
            'wikipedia.org': 95,
            'gov': 90,
            'edu': 85,
            'stackoverflow.com': 80,
            'github.com': 75
        }
        
        for auth_domain, score in authority_domains.items():
            if auth_domain in domain:
                return float(score)
        
        # Default scores based on TLD
        if '.gov' in domain or '.edu' in domain:
            return 85.0
        elif '.org' in domain:
            return 60.0
        else:
            return 50.0


# Global instance (will be initialized in app)
concurrent_collector = None
