#!/usr/bin/env python3
"""
Main application entry point for Azure App Service Linux
This file is the primary entry point that Azure will use
"""

import os
import sys
import logging

# Configure logging for Azure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure the app directory is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    # Import the Flask app and SocketIO
    logger.info("Attempting to import Flask app...")
    from app import app, socketio
    
    logger.info("Successfully imported Flask app and SocketIO")
    
    # For gunicorn with gevent worker, we need to use the SocketIO WSGI app
    application = socketio
    
    logger.info("Application configured for Azure App Service Linux")
    
    # Test route to verify the app is working
    @app.route('/test')
    def test_route():
        return {'status': 'success', 'message': 'App is working!'}, 200
    
except Exception as e:
    logger.error(f"Error importing application: {e}")
    import traceback
    traceback.print_exc()
    
    # Fallback - create a simple Flask app that shows the error
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def error_page():
        return f"""
        <h1>Application Import Error</h1>
        <p>Error: {str(e)}</p>
        <p>Check the Azure logs for more details.</p>
        <p>Python version: {sys.version}</p>
        <p>Python path: {sys.path}</p>
        <pre>{traceback.format_exc()}</pre>
        """, 500
    
    @application.route('/health')
    def health():
        return {'status': 'error', 'message': str(e)}, 500

if __name__ == "__main__":
    # For local testing
    port = int(os.environ.get('PORT', 8000))
    
    if os.environ.get('WEBSITE_SITE_NAME'):
        # Running on Azure App Service
        logger.info(f"Starting application on Azure App Service, port {port}")
        socketio.run(app, host='0.0.0.0', port=port, debug=False)
    else:
        # Local development
        logger.info(f"Starting application locally on port {port}")
        socketio.run(app, host='0.0.0.0', port=port, debug=True)