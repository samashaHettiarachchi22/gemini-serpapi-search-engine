"""
Application entry point
Run this file to start the Flask server
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = app.config.get('PORT', 5000)
    debug = app.config.get('DEBUG', True)
    app.run(debug=debug, host='0.0.0.0', port=port)
