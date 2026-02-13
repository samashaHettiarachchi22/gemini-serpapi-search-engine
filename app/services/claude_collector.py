"""
Claude-based Data Collector
Same analytics as Gemini, but using Claude API
"""

import time
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from app.services.claude_service import claude_service
from app.models.optimized_tracking import search_tracking_db_optimized
from app.utils.logging_system import analytics_logger


class ClaudeDataCollector:
    """
    Collect and analyze search data using Claude API
    Same structure as GeminiOnlyCollector but with Claude
    """
    
    def __init__(self, db_handler=None):
        self.service = claude_service
        self.db = db_handler or search_tracking_db_optimized
    
    def collect_claude_snapshot(self, query: str, brand_domains: List[str] = None) -> Dict[str, Any]:
        """
        Complete end-to-end: ask Claude, calculate metrics, save to DB
        Returns snapshot_id and metrics (SAME FORMAT AS GEMINI)
        """
        brand_domains = brand_domains or []
        start = time.time()

        try:
            # Step 1: Ask Claude
            analytics_logger.log_info("Step 1: Asking Claude", extra={'query': query})
            raw = self._ask_claude_comprehensive_analysis(query, brand_domains)
            
            # Step 2: Parse response
            analytics_logger.log_info("Step 2: Parsing Claude response")
            parsed = self._parse_claude_response(raw)
            analytics_logger.log_info("Parsed data", extra={'parsed_keys': list(parsed.keys())})

            # Step 3: Calculate metrics
            analytics_logger.log_info("Step 3: Calculating metrics")
            metrics = self._calculate_metrics_from_claude(parsed, brand_domains)

            # Step 4: Structure data for database
            analytics_logger.log_info("Step 4: Structuring for storage")
            snapshot_data, citations_data = self._structure_for_storage(
                query, parsed, metrics, brand_domains
            )

            # Step 5: Save to database
            analytics_logger.log_info("Step 5: Saving to database")
            elapsed_ms = int((time.time() - start) * 1000)
            log_data = {
                'query': query,
                'gemini_status': 'skipped',
                'serpapi_status': 'skipped',
                'database_status': 'success',
                'total_time_ms': elapsed_ms,
                'log_level': 'INFO'
            }

            snapshot_id = self.db.save_complete_snapshot(
                snapshot_data=snapshot_data,
                citations_data=citations_data,
                positions_data=[],
                log_data=log_data
            )
            
            analytics_logger.log_info(
                f"Claude-only snapshot saved",
                extra={'snapshot_id': snapshot_id, 'query': query}
            )

            return {
                'status': 'success',
                'snapshot_id': snapshot_id,
                'metrics': metrics,
                'execution_time_ms': elapsed_ms,
                'debug': {
                    'claude_raw_response': raw,
                    'parsed_keys': list(parsed.keys()),
                    'citations_count': len(parsed.get('citations', []))
                }
            }

        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            analytics_logger.log_error(
                f"Failed in collect_claude_snapshot", 
                error=e, 
                extra={'query': query, 'error_type': type(e).__name__}
            )
            return {
                'status': 'error',
                'message': f"{type(e).__name__}: {str(e)}",
                'execution_time_ms': elapsed_ms
            }
    
    def _ask_claude_comprehensive_analysis(self, query: str, brand_domains: List[str]) -> str:
        prompt = f"""
## Role
You are the Claude Search Answer Engine. Your goal is to synthesize a definitive "AI Overview" for a specific user query using real-time search simulation logic.

## Task
Analyze the query: "{query}"
Generate a high-relevance response grounded in actual web data.

## Search Engine Constraints
- **Evidence-First:** Do not state facts that cannot be attributed to a citation.
- **Brand Neutrality:** Mention brands only if they are the subject of the query or represent the primary authority on the topic.
- **Zero Hallucination:** If no real-world source is known, do not "hallucinate". Instead, omit the citation and adjust the confidence of the statement.

## Output Schema (JSON Only)
{{
  "intent": {{
    "type": "informational | transactional | navigational",
    "confidence": 0.85,
    "reasoning": "Brief explanation of intent classification"
  }},
  "ai_overview": {{
    "text": "A 2-4 sentence comprehensive answer that directly addresses the query. Be specific and factual."
  }},
  "citations": [
    {{
      "url": "https://example.com/article",
      "title": "Article Title from Source",
      "snippet": "Specific excerpt from the source that supports the AI overview",
      "source_type": "Blog | News | Documentation | Review | SaaS | Marketplace",
      "authority_estimate": 85,
      "sentiment": "positive | neutral | negative",
      "ai_reusability": "High | Medium | Low"
    }}
  ],
  "domain_summary": [
    {{
      "domain": "example.com",
      "count": 2,
      "authority": "High | Medium | Low"
    }}
  ],
  "top_recommendation": {{
    "domain": "example.com",
    "reasoning": "Why this is the top source"
  }},
  "runner_ups": [
    {{
      "domain": "alternative.com",
      "reasoning": "Why this is also valuable"
    }}
  ]
}}

## Final Rule
Return ONLY valid JSON. No markdown code blocks, no conversational text."""

        try:
            result = self.service.generate_content(prompt, max_tokens=2000)
            return result['text']
        except Exception as e:
            analytics_logger.log_error("Claude call failed", error=e)
            return json.dumps({
                "intent": {"type": "informational", "confidence": 0.5, "reasoning": "fallback"},
                "ai_overview": {"text": ""},
                "citations": [],
                "domain_summary": [],
                "top_recommendation": None,
                "runner_ups": []
            })
    
    def _parse_claude_response(self, raw_text: str) -> Dict[str, Any]:
        # Try to extract first JSON object
        m = re.search(r'(\{[\s\S]*\})', raw_text)
        if not m:
            return {
                "intent": {"type": "informational", "confidence": 0.5, "reasoning": "fallback"},
                "ai_overview": {"text": ""},
                "citations": [],
                "domain_summary": [],
                "top_recommendation": None,
                "runner_ups": []
            }
        try:
            data = json.loads(m.group(1))
        except Exception:
            return {
                "intent": {"type": "informational", "confidence": 0.5, "reasoning": "parse-failed"},
                "ai_overview": {"text": ""},
                "citations": [],
                "domain_summary": [],
                "top_recommendation": None,
                "runner_ups": []
            }

        data.setdefault('intent', {"type": "informational", "confidence": 0.5, "reasoning": ""})
        data.setdefault('ai_overview', {"text": ""})
        data.setdefault('citations', [])
        data.setdefault('domain_summary', [])
        data.setdefault('top_recommendation', None)
        data.setdefault('runner_ups', [])
        return data
    
    def _calculate_metrics_from_claude(self, parsed: Dict[str, Any], brand_domains: List[str]) -> Dict[str, Any]:
        """Calculate visibility, share of voice, intensity from Claude outputs"""
        ai_overview = parsed.get('ai_overview', {})
        if isinstance(ai_overview, str):
            ai_overview_text = ai_overview
        else:
            ai_overview_text = ai_overview.get('text', '') if isinstance(ai_overview, dict) else ''
        
        citations = parsed.get('citations', [])
        if not isinstance(citations, list):
            citations = []
        
        domain_summary = parsed.get('domain_summary', [])
        if not isinstance(domain_summary, list):
            domain_summary = []
        
        top_recommendation = parsed.get('top_recommendation')
        if isinstance(top_recommendation, str):
            top_rec_domain = top_recommendation.lower()
        elif isinstance(top_recommendation, dict):
            top_rec_domain = top_recommendation.get('domain', '').lower()
        else:
            top_rec_domain = ''
        
        total_citations = len(citations)
        
        if not domain_summary and citations:
            domain_counts = {}
            for citation in citations:
                url = citation.get('url', '')
                if url:
                    domain = urlparse(url).netloc.lower().replace('www.', '')
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
            domain_summary = [{'domain': d, 'count': c} for d, c in domain_counts.items()]
        
        brand_count = 0
        brand_mentioned = False
        
        for domain_info in domain_summary:
            domain = domain_info.get('domain', '').lower()
            count = domain_info.get('count', 0)
            if any(brand.lower() in domain for brand in brand_domains):
                brand_count += count
                brand_mentioned = True
        
        if not brand_mentioned and ai_overview_text:
            brand_mentioned = any(brand.lower() in ai_overview_text.lower() for brand in brand_domains)
        
        total_domain_counts = sum(d.get('count', 0) for d in domain_summary if isinstance(d, dict))
        share_of_voice_percentage = (brand_count / total_domain_counts * 100) if total_domain_counts > 0 else 0.0
        
        visibility_score = 0.0
        if brand_mentioned and ai_overview_text:
            visibility_score += 40
        if top_rec_domain and any(brand.lower() in top_rec_domain for brand in brand_domains):
            visibility_score += 30
        brand_in_citations = any(
            any(brand.lower() in citation.get('url', '').lower() for brand in brand_domains)
            for citation in citations
        )
        if brand_in_citations:
            visibility_score += 20
        if brand_count > 0:
            visibility_score += 10
        visibility_score = min(100.0, visibility_score)
        
        intensity_score = min(100.0, total_citations * 8.0)
        
        return {
            'total_citations': total_citations,
            'brand_mentioned': brand_mentioned,
            'brand_citations': brand_count,
            'share_of_voice_percentage': round(share_of_voice_percentage, 2),
            'visibility_score': round(visibility_score, 2),
            'intensity_score': round(intensity_score, 2),
            'domain_summary': domain_summary
        }
    
    def _structure_for_storage(self, query: str, parsed: Dict[str, Any], 
                               metrics: Dict[str, Any], brand_domains: List[str]) -> tuple:
        """Structure data for database tables"""
        intent = parsed.get('intent', {})
        if not isinstance(intent, dict):
            intent = {'type': 'informational', 'confidence': 0.5}
        
        ai_overview = parsed.get('ai_overview', {})
        if isinstance(ai_overview, str):
            ai_overview_text = ai_overview
            has_ai_overview = bool(ai_overview)
        elif isinstance(ai_overview, dict):
            ai_overview_text = ai_overview.get('text', '')
            has_ai_overview = bool(ai_overview_text)
        else:
            ai_overview_text = ''
            has_ai_overview = False
        
        citations = parsed.get('citations', [])
        if not isinstance(citations, list):
            citations = []
        
        snapshot_data = {
            'query': query,
            'timestamp': datetime.utcnow(),
            'country': 'us',
            'language': 'en',
            'google_domain': 'google.com',
            'intent_type': intent.get('type', 'informational'),
            'intent_confidence': intent.get('confidence', 0.5),
            'has_knowledge_graph': False,
            'has_answer_box': False,
            'has_ai_overview': has_ai_overview,
            'has_featured_snippet': False,
            'has_related_questions': False,
            'brand_mentioned': metrics['brand_mentioned'],
            'ai_overview_text': ai_overview_text,
            'total_citations': metrics['total_citations'],
            'brand_citations': metrics['brand_citations'],
            'total_organic_results': 0,
            'brand_organic_positions': 0,
            'visibility_score': metrics['visibility_score'],
            'intensity_score': metrics['intensity_score'],
            'share_of_voice_percentage': metrics['share_of_voice_percentage'],
            'category': 'claude-only',
            'created_at': datetime.utcnow()
        }
        
        citations_data = []
        for idx, citation in enumerate(citations):
            url = citation.get('url', '')
            domain = urlparse(url).netloc.lower().replace('www.', '') if url else 'unknown'
            is_brand = any(brand.lower() in domain for brand in brand_domains)
            
            citations_data.append({
                'domain': domain,
                'url': url,
                'title': citation.get('title', ''),
                'source_type': citation.get('source_type', 'NEUTRAL'),
                'is_brand': is_brand,
                'authority_score': citation.get('authority_estimate', 50.0),
                'sentiment': citation.get('sentiment', 'neutral'),
                'ai_reusability_score': citation.get('ai_reusability', 'Medium'),
                'citation_index': idx,
                'timestamp': datetime.utcnow()
            })
        
        return snapshot_data, citations_data

    
    def analyze_search_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze search intent using Claude
        Returns: intent_type, confidence
        """
        prompt = f"""Analyze this search query and determine the user's intent.

Query: "{query}"

Classify into ONE of these categories:
- informational: User wants to learn/find information
- transactional: User wants to buy/download/sign up
- navigational: User wants to find a specific website/brand

Respond in JSON format:
{{
    "intent_type": "informational|transactional|navigational",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

        try:
            result = self.service.generate_content(prompt, max_tokens=200)
            response_text = result['text'].strip()
            
            # Extract JSON from response
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            data = json.loads(response_text)
            
            return {
                "intent_type": data.get("intent_type", "informational"),
                "confidence": float(data.get("confidence", 0.7))
            }
        except Exception as e:
            # Fallback
            return {
                "intent_type": "informational",
                "confidence": 0.5
            }
    
    def analyze_citation_quality(self, citations: List[Dict[str, Any]], brand_domains: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze citation sources for quality, sentiment, and reusability
        """
        if not citations:
            return []
        
        analyzed_citations = []
        
        for citation in citations[:10]:  # Limit to 10 citations
            domain = citation.get('domain', '')
            title = citation.get('title', '')
            snippet = citation.get('snippet', '')
            
            # Check if brand
            is_brand = any(brand in domain.lower() for brand in brand_domains) if brand_domains else False
            
            prompt = f"""Analyze this citation source:

Domain: {domain}
Title: {title}
Snippet: {snippet[:200]}

Provide analysis in JSON format:
{{
    "source_type": "owned|competitor|authority|neutral",
    "authority_score": 0-100,
    "sentiment": "positive|neutral|negative",
    "ai_reusability_score": "High|Medium|Low",
    "reasoning": "brief explanation"
}}"""

            try:
                result = self.service.generate_content(prompt, max_tokens=250)
                response_text = result['text'].strip()
                
                # Extract JSON
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0].strip()
                
                data = json.loads(response_text)
                
                analyzed_citations.append({
                    "domain": domain,
                    "url": citation.get('url', ''),
                    "title": title,
                    "source_type": data.get("source_type", "neutral"),
                    "is_brand": is_brand,
                    "authority_score": float(data.get("authority_score", 50)),
                    "sentiment": data.get("sentiment", "neutral"),
                    "ai_reusability_score": data.get("ai_reusability_score", "Medium"),
                    "citation_index": citation.get('position', 0)
                })
                
            except Exception as e:
                # Fallback with basic data
                analyzed_citations.append({
                    "domain": domain,
                    "url": citation.get('url', ''),
                    "title": title,
                    "source_type": "neutral",
                    "is_brand": is_brand,
                    "authority_score": 50.0,
                    "sentiment": "neutral",
                    "ai_reusability_score": "Medium",
                    "citation_index": citation.get('position', 0)
                })
        
        return analyzed_citations
    
    def analyze_ai_overview(self, ai_overview_text: str, brand_domains: List[str]) -> Dict[str, Any]:
        """
        Analyze AI overview for brand mentions and citations
        """
        if not ai_overview_text:
            return {
                "brand_mentioned": False,
                "total_citations": 0,
                "brand_citations": 0
            }
        
        prompt = f"""Analyze this AI Overview text:

"{ai_overview_text}"

Brand domains to check: {', '.join(brand_domains) if brand_domains else 'None'}

Provide analysis in JSON format:
{{
    "brand_mentioned": true/false,
    "total_citations_estimated": number,
    "brand_citations_estimated": number,
    "key_topics": ["topic1", "topic2"]
}}"""

        try:
            result = self.service.generate_content(prompt, max_tokens=200)
            response_text = result['text'].strip()
            
            # Extract JSON
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            data = json.loads(response_text)
            
            return {
                "brand_mentioned": data.get("brand_mentioned", False),
                "total_citations": int(data.get("total_citations_estimated", 0)),
                "brand_citations": int(data.get("brand_citations_estimated", 0))
            }
        except Exception as e:
            return {
                "brand_mentioned": False,
                "total_citations": 0,
                "brand_citations": 0
            }
    
    def calculate_scores(self, 
                        has_ai_overview: bool,
                        brand_mentioned: bool,
                        brand_citations: int,
                        total_organic_results: int,
                        brand_organic_positions: int) -> Dict[str, float]:
        """
        Calculate visibility and intensity scores
        Same algorithm as Gemini version
        """
        visibility_score = 0.0
        intensity_score = 0.0
        
        # Visibility: Are you present?
        if has_ai_overview and brand_mentioned:
            visibility_score += 50
        if brand_organic_positions > 0:
            visibility_score += 50
        
        # Intensity: How strong is presence?
        if brand_citations > 0:
            intensity_score += min(brand_citations * 20, 60)
        if brand_organic_positions > 0:
            intensity_score += min(brand_organic_positions * 20, 40)
        
        # Share of voice
        sov = 0.0
        if total_organic_results > 0:
            sov = (brand_organic_positions / total_organic_results) * 100
        
        return {
            "visibility_score": min(visibility_score, 100),
            "intensity_score": min(intensity_score, 100),
            "share_of_voice_percentage": round(sov, 2)
        }
    
    def collect_all_data(self, 
                        query: str,
                        brand_domains: List[str],
                        serp_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method: Analyze all data using Claude
        Returns structured data ready for database
        """
        start_time = time.time()
        
        # Extract SERP features
        has_ai_overview = bool(serp_data.get('ai_overview'))
        ai_overview_text = serp_data.get('ai_overview', {}).get('text', '')
        citations = serp_data.get('citations', [])
        organic_results = serp_data.get('organic_results', [])
        
        # Feature detection
        features = {
            "has_knowledge_graph": bool(serp_data.get('knowledge_graph')),
            "has_answer_box": bool(serp_data.get('answer_box')),
            "has_ai_overview": has_ai_overview,
            "has_featured_snippet": bool(serp_data.get('featured_snippet')),
            "has_related_questions": bool(serp_data.get('related_questions'))
        }
        
        # 1. Analyze intent
        intent_data = self.analyze_search_intent(query)
        
        # 2. Analyze AI overview
        ai_analysis = self.analyze_ai_overview(ai_overview_text, brand_domains)
        
        # 3. Analyze citations
        analyzed_citations = self.analyze_citation_quality(citations, brand_domains)
        
        # 4. Analyze organic results
        brand_organic_count = 0
        organic_positions = []
        
        for idx, result in enumerate(organic_results[:10], 1):
            domain = result.get('domain', '')
            is_brand = any(brand in domain.lower() for brand in brand_domains) if brand_domains else False
            
            if is_brand:
                brand_organic_count += 1
            
            organic_positions.append({
                "position": idx,
                "domain": domain,
                "url": result.get('url', ''),
                "is_brand": is_brand
            })
        
        # 5. Calculate scores
        scores = self.calculate_scores(
            has_ai_overview=has_ai_overview,
            brand_mentioned=ai_analysis['brand_mentioned'],
            brand_citations=ai_analysis['brand_citations'],
            total_organic_results=len(organic_results),
            brand_organic_positions=brand_organic_count
        )
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "snapshot_data": {
                "query": query,
                "intent_type": intent_data['intent_type'],
                "intent_confidence": intent_data['confidence'],
                **features,
                "brand_mentioned": ai_analysis['brand_mentioned'],
                "ai_overview_text": ai_overview_text[:500] if ai_overview_text else None,
                "total_citations": len(analyzed_citations),
                "brand_citations": ai_analysis['brand_citations'],
                "total_organic_results": len(organic_results),
                "brand_organic_positions": brand_organic_count,
                "visibility_score": scores['visibility_score'],
                "intensity_score": scores['intensity_score'],
                "share_of_voice_percentage": scores['share_of_voice_percentage'],
                "processing_time_ms": processing_time_ms,
                "category": "claude-analytics"
            },
            "citations_data": analyzed_citations,
            "positions_data": organic_positions
        }
    
    def analyze_without_serp(self, query: str, brand_domains: List[str]) -> Dict[str, Any]:
        """
        Analyze query using ONLY Claude (no SerpAPI data)
        Claude simulates what AI overview and citations might look like
        """
        start_time = time.time()
        
        prompt = f"""You are analyzing this search query: "{query}"

Generate a simulated Google AI Overview response with citations.

Respond in JSON format:
{{
    "intent_type": "informational|transactional|navigational",
    "confidence": 0.0-1.0,
    "ai_overview_text": "2-3 sentence AI overview answer",
    "citations": [
        {{
            "url": "https://example.com",
            "title": "Page title",
            "snippet": "Brief excerpt",
            "source_type": "Blog|News|Docs|SaaS",
            "authority": 0.0-1.0,
            "sentiment": "positive|neutral|negative"
        }}
    ]
}}

Include 3-5 realistic citations."""

        try:
            result = self.service.generate_content(prompt, max_tokens=1000)
            response_text = result['text'].strip()
            
            # Extract JSON
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            data = json.loads(response_text)
            
            # Process citations
            citations_data = []
            brand_citations = 0
            
            for idx, cit in enumerate(data.get('citations', []), 1):
                domain = cit.get('url', '').split('/')[2] if '//' in cit.get('url', '') else ''
                is_brand = any(brand in domain.lower() for brand in brand_domains) if brand_domains else False
                
                if is_brand:
                    brand_citations += 1
                
                citations_data.append({
                    "citation_index": idx,
                    "url": cit.get('url', ''),
                    "title": cit.get('title', ''),
                    "domain": domain,
                    "source_type": cit.get('source_type', 'Unknown'),
                    "is_brand": is_brand,
                    "authority_score": cit.get('authority', 0.5),
                    "sentiment": cit.get('sentiment', 'neutral'),
                    "ai_reusability_score": "Medium"
                })
            
            # Calculate scores
            scores = self.calculate_scores(
                has_ai_overview=True,
                brand_mentioned=brand_citations > 0,
                brand_citations=brand_citations,
                total_organic_results=0,
                brand_organic_positions=0
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                "snapshot_data": {
                    "query": query,
                    "intent_type": data.get('intent_type', 'informational'),
                    "intent_confidence": data.get('confidence', 0.7),
                    "has_knowledge_graph": False,
                    "has_answer_box": False,
                    "has_ai_overview": True,
                    "has_featured_snippet": False,
                    "has_related_questions": False,
                    "brand_mentioned": brand_citations > 0,
                    "ai_overview_text": data.get('ai_overview_text', '')[:500],
                    "total_citations": len(citations_data),
                    "brand_citations": brand_citations,
                    "total_organic_results": 0,
                    "brand_organic_positions": 0,
                    "visibility_score": scores['visibility_score'],
                    "intensity_score": scores['intensity_score'],
                    "share_of_voice_percentage": scores['share_of_voice_percentage'],
                    "processing_time_ms": processing_time_ms,
                    "category": "claude-only"
                },
                "citations_data": citations_data,
                "positions_data": [],
                "log_data": {
                    "query": query,
                    "serpapi_status": "skipped",
                    "gemini_status": "skipped",
                    "database_status": "pending",
                    "total_time_ms": processing_time_ms,
                    "log_level": "INFO"
                }
            }
            
        except Exception as e:
            # Return minimal data on error
            return {
                "snapshot_data": {
                    "query": query,
                    "intent_type": "informational",
                    "intent_confidence": 0.5,
                    "has_ai_overview": False,
                    "category": "claude-only",
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                },
                "citations_data": [],
                "positions_data": [],
                "log_data": {
                    "query": query,
                    "error_message": str(e),
                    "log_level": "ERROR"
                }
            }


# Singleton instance
claude_collector = ClaudeDataCollector()
