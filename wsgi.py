"""
WSGI entry point for Gunicorn deployment
"""

import os
import sys

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app and SocketIO
from app import app, socketio

# For Gunicorn, we need to expose the SocketIO WSGI application
application = socketio.wsgi_app

if __name__ == "__main__":
    # For local development
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)