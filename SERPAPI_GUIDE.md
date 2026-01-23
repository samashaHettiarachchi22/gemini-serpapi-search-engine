# SerpApi Integration for Answer Engine Tracking

This project now includes SerpApi integration to track Google answer engine results in the top half of search pages.

## Setup

1. **Get a SerpApi API Key**
   - Sign up at https://serpapi.com/
   - Get your API key from the dashboard

2. **Configure Environment Variables**

   Add to your `.env` file:

   ```
   SERPAPI_API_KEY=your_serpapi_key_here
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## API Endpoints

All SerpApi endpoints are available under `/api/serpapi/`

### 1. Get Answer Box / Featured Snippet

**POST** `/api/serpapi/answer-box`

Extracts Google's direct answer box or featured snippet.

```json
{
  "query": "what is the capital of sri lanka",
  "gl": "lk",
  "hl": "en"
}
```

**Response:**

```json
{
  "success": true,
  "query": "what is the capital of sri lanka",
  "found": true,
  "data": {
    "kind": "answer_box",
    "type": "organic_result",
    "title": "Sri Lanka",
    "answer": "Colombo",
    "source": "https://example.com",
    "displayed_link": "example.com"
  }
}
```

### 2. Get Top Half Results (Comprehensive)

**POST** `/api/serpapi/top-half`

Extracts all answer engine elements from the top half of Google SERP:

- Answer box / Featured snippet
- Knowledge graph
- People Also Ask (PAA)
- Top 3 organic results

```json
{
  "query": "python programming language",
  "gl": "us",
  "hl": "en"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "query": "python programming language",
    "answer_box": {...},
    "knowledge_graph": {...},
    "people_also_ask": [...],
    "organic_results": [...],
    "has_answer_engine_result": true
  }
}
```

### 3. Get People Also Ask (PAA)

**POST** `/api/serpapi/people-also-ask`

Extracts PAA questions and answers.

```json
{
  "query": "how to learn python",
  "gl": "us"
}
```

### 4. Get Knowledge Graph

**POST** `/api/serpapi/knowledge-graph`

Extracts knowledge panel data.

```json
{
  "query": "elon musk",
  "gl": "us"
}
```

### 5. Full Search Results

**POST** `/api/serpapi/search`

Returns complete raw SerpApi response (all data).

## Query Parameters

- `query` (required): Search query string
- `gl` (optional): Country code (default: "us")
  - Examples: "us", "uk", "lk", "au", "ca"
- `hl` (optional): Language code (default: "en")
  - Examples: "en", "es", "fr", "de"
- `google_domain` (optional): Google domain (default: "google.com")
  - Examples: "google.com", "google.lk", "google.co.uk"

## Using the Example Script

Run the included example script to see all endpoints in action:

```bash
# Make sure your Flask app is running first
python run.py

# In another terminal, run the example
python scripts/serpapi_example.py
```

## Building an Answer Engine Tracker

To track answer engine results over time:

1. **Schedule periodic searches** for your keywords
2. **Store results** with timestamps in a database
3. **Track changes** in:
   - Featured snippet presence/absence
   - Answer box content changes
   - PAA question variations
   - Knowledge graph visibility
   - Position shifts in organic results

Example tracking logic:

```python
import sqlite3
from datetime import datetime
from app.services.serpapi_service import serpapi_service

# Initialize service
serpapi_service.initialize(api_key, endpoint)

# Fetch and extract
results = serpapi_service.fetch_google_search(query="your keyword")
top_half = serpapi_service.extract_top_half_results(results)

# Store in DB
conn = sqlite3.connect('tracking.db')
conn.execute('''
    INSERT INTO serp_history
    (timestamp, query, has_answer_box, has_knowledge_graph, paa_count)
    VALUES (?, ?, ?, ?, ?)
''', (
    datetime.now(),
    top_half['query'],
    bool(top_half['answer_box']),
    bool(top_half['knowledge_graph']),
    len(top_half['people_also_ask'])
))
conn.commit()
```

## What SerpApi Provides

✅ Structured JSON data for all SERP elements  
✅ Answer boxes and featured snippets  
✅ Knowledge graph panels  
✅ People Also Ask questions  
✅ Organic results with positions  
✅ Rich snippets and SERP features

❌ Does NOT provide built-in time-series tracking  
❌ Does NOT provide automated rank change alerts  
❌ Does NOT include analytics dashboards

You get the **data layer** — tracking and analytics are up to your implementation.

## Rate Limits & Pricing

- Check SerpApi's current pricing at https://serpapi.com/pricing
- Free tier available for testing
- Consider rate limits when scaling to many keywords

## Best Practices

1. **Cache results** to avoid redundant API calls
2. **Handle API errors** gracefully (rate limits, network issues)
3. **Validate JSON structure** as Google changes SERP features
4. **Use specific queries** for better tracking accuracy
5. **Store raw responses** for future reprocessing if needed

## Testing

Test the SerpApi service:

```bash
pytest tests/test_routes.py -k serpapi
```

## Troubleshooting

**Error: "SerpApi API key not configured"**

- Make sure `SERPAPI_API_KEY` is set in your `.env` file
- Restart the Flask app after adding the key

**Error: "No answer box found"**

- Not all queries have answer boxes
- Try different query types (factual questions work best)
- Check different country/language combinations

**Empty results**

- Verify your API key is valid
- Check you haven't exceeded rate limits
- Ensure the query parameters are correct
