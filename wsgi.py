"""
WSGI entry point for Azure App Service
"""

import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from app import app, socketio
    
    # For SocketIO with gunicorn, we need to use the SocketIO WSGI app
    application = socketio
    
    print("WSGI application loaded successfully")
    
except Exception as e:
    print(f"Error loading WSGI application: {e}")
    import traceback
    traceback.print_exc()
    
    # Fallback - create a simple Flask app that shows the error
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def error_page():
        return f"Application startup error: {str(e)}", 500

if __name__ == "__main__":
    # For local testing
    try:
        socketio.run(app, host='0.0.0.0', port=8000, debug=False)
    except Exception as e:
        print(f"Error running application: {e}")
        app.run(host='0.0.0.0', port=8000, debug=False)