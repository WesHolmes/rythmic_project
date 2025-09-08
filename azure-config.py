"""
Azure App Service configuration helper
"""
import os

def configure_for_azure():
    """Configure environment variables for Azure deployment"""
    
    # Set production environment
    os.environ.setdefault('FLASK_ENV', 'production')
    os.environ.setdefault('FLASK_DEBUG', 'False')
    
    # Ensure required environment variables are set
    required_vars = [
        'SECRET_KEY',
        'OPENAI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Warning: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please configure these in Azure App Service Configuration settings")
    
    return len(missing_vars) == 0