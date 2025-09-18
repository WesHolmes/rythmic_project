"""
WSGI entry point for Azure App Service
"""

from app import app, socketio

# This is what gunicorn will use
application = socketio

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=8000, debug=False)