"""
Azure App Service Static File Handler

This module provides enhanced static file serving for Azure App Service
to resolve MIME type issues and 500 errors with static files.
"""

import os
import mimetypes
from flask import Response, abort, current_app


class AzureStaticFileHandler:
    """Handle static file serving for Azure App Service"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the static file handler with Flask app"""
        self.app = app
        
        # Set up MIME types
        mimetypes.init()
        mimetypes.add_type('text/css', '.css')
        mimetypes.add_type('application/javascript', '.js')
        mimetypes.add_type('application/json', '.json')
        mimetypes.add_type('font/woff', '.woff')
        mimetypes.add_type('font/woff2', '.woff2')
        mimetypes.add_type('font/ttf', '.ttf')
        mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
        mimetypes.add_type('image/svg+xml', '.svg')
        
        # Register the static file handler
        app.add_url_rule('/static/<path:filename>', 
                        endpoint='azure_static', 
                        view_func=self.serve_static_file)
    
    def serve_static_file(self, filename):
        """Serve static files with proper MIME types"""
        try:
            # Get the static folder path
            static_folder = current_app.static_folder
            if not static_folder:
                static_folder = os.path.join(current_app.root_path, 'static')
            
            file_path = os.path.join(static_folder, filename)
            
            # Security check - ensure file is within static folder
            if not os.path.abspath(file_path).startswith(os.path.abspath(static_folder)):
                abort(403)
            
            # Check if file exists
            if not os.path.exists(file_path):
                abort(404)
            
            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determine MIME type
            mime_type = self.get_mime_type(filename)
            
            # Create response
            response = Response(content, mimetype=mime_type)
            
            # Add cache headers for static files
            response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year
            response.headers['ETag'] = f'"{hash(content)}"'
            
            # Add security headers
            if filename.endswith('.js'):
                response.headers['X-Content-Type-Options'] = 'nosniff'
            
            return response
            
        except Exception as e:
            print(f"Error serving static file {filename}: {e}")
            abort(500)
    
    def get_mime_type(self, filename):
        """Get the correct MIME type for a file"""
        # Get file extension
        _, ext = os.path.splitext(filename.lower())
        
        # Define MIME type mappings
        mime_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.xml': 'application/xml',
            '.txt': 'text/plain'
        }
        
        # Return specific MIME type or guess from mimetypes module
        return mime_types.get(ext) or mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def configure_azure_static_files(app):
    """Configure Azure-specific static file handling"""
    if app.config.get('AZURE_APP_SERVICE'):
        handler = AzureStaticFileHandler(app)
        print("Azure static file handler configured")
        return handler
    return None