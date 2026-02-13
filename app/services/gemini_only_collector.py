import re
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from app.services.gemini_service import gemini_service
from app.models.optimized_tracking import SearchSnapshot, CitationSource, ExecutionLog, search_tracking_db_optimized
from app.utils.logging_system import analytics_logger, execution_tracker
from sqlalchemy.orm import sessionmaker
from config import Config

class GeminiOnlyCollector:
    def __init__(self, db_handler=None):
        self.gemini = gemini_service
        self.db = db_handler or search_tracking_db_optimized

    def collect_gemini_snapshot(self, query: str, brand_domains: List[str]=None, gl: str='us', hl: str='en') -> Dict[str, Any]:
        """
        Complete end-to-end: ask Gemini, calculate metrics, save to DB
        Returns snapshot_id and metrics
        """
        brand_domains = brand_domains or []
        start = time.time()

        try:
            # Step 1: Ask Gemini
            analytics_logger.log_info("Step 1: Asking Gemini", extra={'query': query})
            raw = self._ask_gemini_comprehensive_analysis(query, brand_domains, gl, hl)
            
            # Step 2: Parse response
            analytics_logger.log_info("Step 2: Parsing Gemini response")
            parsed = self._parse_gemini_response(raw)
            analytics_logger.log_info("Parsed data", extra={'parsed_keys': list(parsed.keys())})

            # Step 3: Calculate metrics
            analytics_logger.log_info("Step 3: Calculating metrics")
            metrics = self._calculate_metrics_from_gemini(parsed, brand_domains)

            # Step 4: Structure data for database
            analytics_logger.log_info("Step 4: Structuring for storage")
            snapshot_data, citations_data = self._structure_for_storage(
                query, parsed, metrics, brand_domains, gl, hl
            )

            # Step 5: Save to database
            analytics_logger.log_info("Step 5: Saving to database")
            elapsed_ms = int((time.time() - start) * 1000)
            log_data = {
                'query': query,
                'gemini_status': 'success',
                'serpapi_status': 'skipped',  # not used for gemini-only
                'database_status': 'success',
                'gemini_time_ms': elapsed_ms,
                'total_time_ms': elapsed_ms,
                'log_level': 'INFO'
            }

            snapshot_id = self.db.save_complete_snapshot(
                snapshot_data=snapshot_data,
                citations_data=citations_data,
                positions_data=[],  # no organic positions for gemini-only
                log_data=log_data
            )
            
            analytics_logger.log_info(
                f"Gemini-only snapshot saved",
                extra={'snapshot_id': snapshot_id, 'query': query}
            )

            return {
                'status': 'success',
                'snapshot_id': snapshot_id,
                'metrics': metrics,
                'execution_time_ms': elapsed_ms,
                'debug': {
                    'gemini_raw_response': raw,  # Full response
                    'parsed_keys': list(parsed.keys()),
                    'citations_count': len(parsed.get('citations', []))
                }
            }

        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            analytics_logger.log_error(
                f"Failed in collect_gemini_snapshot", 
                error=e, 
                extra={'query': query, 'error_type': type(e).__name__}
            )
            return {
                'status': 'error',
                'message': f"{type(e).__name__}: {str(e)}",
                'execution_time_ms': elapsed_ms
            }

    def _ask_gemini_comprehensive_analysis(self, query: str, brand_domains: List[str], gl: str, hl: str) -> str:
        prompt = f"""
## Role
You are the Google Gemini Search Answer Engine. Your goal is to synthesize a definitive "AI Overview" for a specific user query using real-time search simulation logic.

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



        # DEBUG: Log the actual prompt being sent to Gemini
        print("\n" + "="*80)
        print("🔵 PROMPT SENT TO GEMINI:")
        print("="*80)
        print(prompt)
        print("="*80 + "\n")
        
        # simple retry logic
        attempts = 2
        last_exc = None
        for i in range(attempts):
            try:
                response_text = self.gemini.generate_content(prompt)
                
                # DEBUG: Log the actual response from Gemini
                print("\n" + "="*80)
                print("🟢 RESPONSE FROM GEMINI:")
                print("="*80)
                print(response_text)
                print("="*80 + "\n")
                
                return response_text
            except Exception as e:
                analytics_logger.log_warning("Gemini call failed, retrying", extra={'attempt': i, 'error': str(e)})
                last_exc = e
        
        # final fallback: return empty JSON structure as text
        analytics_logger.log_error("Gemini call failed after retries", error=last_exc)
        return json.dumps({
            "intent": {"type": "informational", "confidence": 0.5, "reasoning": "fallback"},
            "ai_overview": {"text": ""},
            "citations": [],
            "domain_summary": [],
            "top_recommendation": None,
            "runner_ups": [],
            "explanation": "fallback due to Gemini failure"
        })
    
    def _parse_gemini_response(self, raw_text: str) -> Dict[str, Any]:
        # Try to extract first JSON object
        m = re.search(r'(\{[\s\S]*\})', raw_text)
        if not m:
            analytics_logger.log_warning("No JSON found in Gemini response; returning fallback", extra={'raw': raw_text[:200]})
            return {
                "intent": {"type": "informational", "confidence": 0.5, "reasoning": "fallback"},
                "ai_overview": {"text": ""},
                "citations": [],
                "domain_summary": [],
                "top_recommendation": None,
                "runner_ups": [],
                "explanation": "no-json"
            }
        try:
            data = json.loads(m.group(1))
        except Exception as e:
            analytics_logger.log_warning("JSON parse failed", extra={'error': str(e), 'snippet': m.group(1)[:200]})
            return {
                "intent": {"type": "informational", "confidence": 0.5, "reasoning": "fallback"},
                "ai_overview": {"text": ""},
                "citations": [],
                "domain_summary": [],
                "top_recommendation": None,
                "runner_ups": [],
                "explanation": "parse-failed"
            }

        # Ensure required keys exist and normalize
        data.setdefault('intent', {"type": "informational", "confidence": 0.5, "reasoning": ""})
        data.setdefault('ai_overview', {"text": ""})
        data.setdefault('citations', [])
        data.setdefault('domain_summary', [])
        data.setdefault('top_recommendation', None)
        data.setdefault('runner_ups', [])
        return data

    def _calculate_metrics_from_gemini(self, parsed: Dict[str, Any], brand_domains: List[str]) -> Dict[str, Any]:
        """
        Calculate visibility, share of voice, intensity from Gemini outputs
        Rule-based, deterministic calculations
        """
        # Extract data - handle various types safely
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
        
        # Handle top_recommendation - can be dict, string, or None
        top_recommendation = parsed.get('top_recommendation')
        if isinstance(top_recommendation, str):
            top_rec_domain = top_recommendation.lower()
        elif isinstance(top_recommendation, dict):
            top_rec_domain = top_recommendation.get('domain', '').lower()
        else:
            top_rec_domain = ''
        
        # Basic counts
        total_citations = len(citations)
        
        # Extract domains from citations if domain_summary is empty
        if not domain_summary and citations:
            domain_counts = {}
            for citation in citations:
                url = citation.get('url', '')
                if url:
                    domain = urlparse(url).netloc.lower().replace('www.', '')
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
            domain_summary = [{'domain': d, 'count': c} for d, c in domain_counts.items()]
        
        # Calculate brand metrics
        brand_count = 0
        brand_mentioned = False
        
        for domain_info in domain_summary:
            domain = domain_info.get('domain', '').lower()
            count = domain_info.get('count', 0)
            if any(brand.lower() in domain for brand in brand_domains):
                brand_count += count
                brand_mentioned = True
        
        # Check if brand mentioned in AI overview text
        if not brand_mentioned and ai_overview_text:
            brand_mentioned = any(brand.lower() in ai_overview_text.lower() for brand in brand_domains)
        
        # Share of voice percentage
        total_domain_counts = sum(d.get('count', 0) for d in domain_summary if isinstance(d, dict))
        share_of_voice_percentage = (brand_count / total_domain_counts * 100) if total_domain_counts > 0 else 0.0
        
        # Visibility score (rule-based, 0-100)
        visibility_score = 0.0
        
        # +40 if brand mentioned in AI overview
        if brand_mentioned and ai_overview_text:
            visibility_score += 40
        
        # +30 if brand is top recommendation (top_rec_domain already extracted above)
        if top_rec_domain and any(brand.lower() in top_rec_domain for brand in brand_domains):
            visibility_score += 30
        
        # +20 if brand in citations
        brand_in_citations = any(
            any(brand.lower() in citation.get('url', '').lower() for brand in brand_domains)
            for citation in citations
        )
        if brand_in_citations:
            visibility_score += 20
        
        # +10 if brand in domain summary
        if brand_count > 0:
            visibility_score += 10
        
        visibility_score = min(100.0, visibility_score)
        
        # Intensity score (normalize citations count to 0-100)
        # Simple scale: 10 citations = ~80 points
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
                               metrics: Dict[str, Any], brand_domains: List[str],
                               gl: str, hl: str) -> tuple:
        """
        Structure data for database tables (same format as SERP flow)
        """
        # Safely extract intent
        intent = parsed.get('intent', {})
        if not isinstance(intent, dict):
            intent = {'type': 'informational', 'confidence': 0.5}
        
        # Safely extract ai_overview
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
        
        # Safely extract citations
        citations = parsed.get('citations', [])
        if not isinstance(citations, list):
            citations = []
        
        # Snapshot data (category is optional - backward compatible)
        snapshot_data = {
            'query': query,
            'timestamp': datetime.utcnow(),
            'country': gl,
            'language': hl,
            'google_domain': 'google.com',
            
            # Intent from Gemini
            'intent_type': intent.get('type', 'informational'),
            'intent_confidence': intent.get('confidence', 0.5),
            
            # Feature flags (Gemini-only = simulated)
            'has_knowledge_graph': False,
            'has_answer_box': False,
            'has_ai_overview': has_ai_overview,
            'has_featured_snippet': False,
            'has_related_questions': False,
            
            # AI Answer metrics
            'brand_mentioned': metrics['brand_mentioned'],
            'ai_overview_text': ai_overview_text,
            'total_citations': metrics['total_citations'],
            'brand_citations': metrics['brand_citations'],
            
            # Organic metrics (not used for gemini-only)
            'total_organic_results': 0,
            'brand_organic_positions': 0,
            
            # Calculated scores
            'visibility_score': metrics['visibility_score'],
            'intensity_score': metrics['intensity_score'],
            'share_of_voice_percentage': metrics['share_of_voice_percentage'],
            
            # Category to distinguish from SERP data (backward compatible - optional)
            'category': 'gemini-only',
            
            # Metadata
            'created_at': datetime.utcnow()
        }
        
        # Citations data
        citations_data = []
        for idx, citation in enumerate(citations):
            url = citation.get('url', '')
            domain = urlparse(url).netloc.lower().replace('www.', '') if url else 'unknown'
            
            # Check if brand
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