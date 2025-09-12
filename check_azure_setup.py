#!/usr/bin/env python3
"""
Script to help determine Azure App Service configuration needs
"""
import os

def check_azure_environment():
    print("=" * 50)
    print("AZURE APP SERVICE CONFIGURATION CHECK")
    print("=" * 50)
    
    # Check if we're in Azure
    azure_indicators = [
        'WEBSITE_SITE_NAME',
        'WEBSITE_RESOURCE_GROUP', 
        'APPSETTING_WEBSITE_SITE_NAME',
        'WEBSITE_OS_TYPE'
    ]
    
    print("Environment Variables:")
    for indicator in azure_indicators:
        value = os.environ.get(indicator, 'Not Set')
        print(f"  {indicator}: {value}")
    
    print()
    
    # Check OS type
    os_type = os.environ.get('WEBSITE_OS_TYPE', 'Unknown')
    print(f"Operating System: {os_type}")
    
    if os_type.lower() == 'linux':
        print("✅ Linux App Service - No web.config needed")
        print("   Azure will use gunicorn automatically")
    elif os_type.lower() == 'windows':
        print("⚠️  Windows App Service - web.config might be helpful")
        print("   But Azure can still auto-detect Flask apps")
    else:
        print("❓ Unknown OS type - Check Azure Portal")
    
    print()
    print("Recommendations:")
    print("1. Try deploying WITHOUT web.config first")
    print("2. If it fails, add web.config for Windows App Service")
    print("3. Check Azure Portal → App Service → Configuration → General Settings")

if __name__ == "__main__":
    check_azure_environment()