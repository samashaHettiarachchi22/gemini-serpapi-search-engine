# Gemini AI Backend API

A Flask-based REST API for interacting with Google's Gemini AI models.

## Features

- 🚀 Generate AI responses using Gemini models
- 📋 List available Gemini models
- 🔒 Secure API key management with environment variables
- 🏗️ Clean architecture with separation of concerns
- 📦 Modular structure with Flask Blueprints

## Project Structure

```
Python/
├── app/                        # Main application package
│   ├── __init__.py            # Flask app factory
│   ├── routes/                # API route handlers
│   │   ├── gemini.py          # Gemini AI endpoints
│   │   └── health.py          # Health check endpoints
│   ├── services/              # Business logic layer
│   │   └── gemini_service.py  # Gemini AI service
│   ├── models/                # Data models
│   └── utils/                 # Utility functions
│       └── validators.py      # Request validators
├── scripts/                   # Utility scripts
│   └── example_client.py      # Example API usage
├── tests/                     # Test suite
│   ├── test_routes.py
│   └── test_gemini_service.py
├── .env                       # Environment variables (not in git)
├── .env.example              # Example environment file
├── .gitignore                # Git ignore rules
├── config.py                 # Configuration settings
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point
└── README.md                 # This file
```

## Setup

### 1. Activate virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Your `.env` file is already configured with the API key.

## Running the Application

```bash
python run.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### GET `/`

API information and available endpoints

### GET `/health`

Health check

### GET `/api/models`

List all available Gemini models

### POST `/api/generate`

Generate AI content from a prompt

**Request body:**

```json
{
  "prompt": "Your question here",
  "model": "models/gemini-2.5-flash" // optional
}
```

**Response:**

```json
{
  "success": true,
  "prompt": "Your question here",
  "response": "AI generated response..."
}
```

## Testing

### Using cURL

```bash
# List models
curl http://localhost:5000/api/models

# Generate content
curl -X POST http://localhost:5000/api/generate -H "Content-Type: application/json" -d "{\"prompt\": \"What is AI?\"}"
```

### Using Python

```bash
python scripts/example_client.py
```

## Security

- ⚠️ Never commit `.env` file to version control
- 🔑 Keep your API keys secure
- 🚫 `.env` is already in `.gitignore`
