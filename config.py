import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_MODEL = 'models/gemini-2.5-flash'
    SERPAPI_API_KEY = os.environ.get('SERPAPI_API_KEY')
    SERPAPI_ENDPOINT = 'https://serpapi.com/search.json'
    
    # Claude (Anthropic) settings
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_API_URL = os.getenv("CLAUDE_API_URL", "https://api.anthropic.com/v1/messages")
    
    # PostgreSQL Database Configuration
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'search_tracking')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
    
    # SQLAlchemy Database URI (using psycopg driver)
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    PORT = 5000

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    PORT = 5000

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
