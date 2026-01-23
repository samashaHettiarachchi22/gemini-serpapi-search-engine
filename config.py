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
