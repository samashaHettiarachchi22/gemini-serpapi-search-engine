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
    
    # Validate SerpApi API key
    if not app.config.get('SERPAPI_API_KEY'):
        raise ValueError("SERPAPI_API_KEY not found in environment variables")
    
    # Validate Claude API key (optional - warning only)
    if not app.config.get('CLAUDE_API_KEY'):
        app.logger.warning("CLAUDE_API_KEY not found - Claude service will not be available")
    
    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.tracking import tracking_bp, init_tracking_services
    
    app.register_blueprint(health_bp)
    app.register_blueprint(tracking_bp, url_prefix='/api/tracking')
    
    # Initialize optimized tracking services
    with app.app_context():
        try:
            init_tracking_services(
                app.config.get('GEMINI_API_KEY'),
                app.config.get('CLAUDE_API_KEY')
            )
            app.logger.info("Optimized tracking services initialized")
        except Exception as e:
            app.logger.error(f"Failed to initialize tracking services: {e}")
    
    # Create optimized database tables
    try:
        from app.models.optimized_tracking import search_tracking_db_optimized
        search_tracking_db_optimized.create_tables()
        app.logger.info("Optimized database tables created")
    except Exception as e:
        app.logger.warning(f"Database table creation: {e}")
    
    return app
