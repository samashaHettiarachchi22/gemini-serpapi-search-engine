from flask import Flask
from config import config
import os

def create_app(config_name=None):
    """Flask application factory"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Validate Gemini API key
    if not app.config.get('GEMINI_API_KEY'):
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    # Validate SerpApi API key (optional - only if you want to use SerpApi)
    if not app.config.get('SERPAPI_API_KEY'):
        app.logger.warning("SERPAPI_API_KEY not found - SerpApi routes will not work")
    
    # Register blueprints
    from app.routes.gemini import gemini_bp
    from app.routes.health import health_bp
    from app.routes.serpapi import serpapi_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(gemini_bp, url_prefix='/api')
    app.register_blueprint(serpapi_bp, url_prefix='/api/serpapi')
    
    return app
