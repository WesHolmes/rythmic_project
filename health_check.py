#!/usr/bin/env python3
"""
Simple health check application for debugging Azure deployment issues
"""

from flask import Flask
import os
import sys

app = Flask(__name__)

@app.route('/')
def home():
    return {
        'status': 'healthy',
        'message': 'Simple Flask app is working',
        'python_version': sys.version,
        'environment': 'azure' if os.environ.get('WEBSITE_SITE_NAME') else 'local'
    }

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

@app.route('/env')
def env_info():
    return {
        'website_site_name': os.environ.get('WEBSITE_SITE_NAME'),
        'port': os.environ.get('PORT'),
        'python_path': sys.path[:3]  # First 3 entries
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)

# For gunicorn
application = app