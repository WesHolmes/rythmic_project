"""
WSGI entry point for Gunicorn deployment
"""

import os
import sys

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app
from app import app

# For Gunicorn, we need to expose the Flask WSGI application
application = app

if __name__ == "__main__":
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)