# Azure App Service Deployment Guide

## Pre-deployment Checklist

### 1. Azure App Service Configuration
Set these environment variables in Azure App Service Configuration:

**Required:**
- `SECRET_KEY` - A secure random string for Flask sessions
- `OPENAI_API_KEY` - Your OpenAI API key for AI features

**Optional (for OAuth):**
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `OUTLOOK_CLIENT_ID` - Microsoft OAuth client ID
- `OUTLOOK_CLIENT_SECRET` - Microsoft OAuth client secret

### 2. Database Configuration
- Default: SQLite (included, good for testing)
- Production: Consider Azure Database for PostgreSQL
- Set `DATABASE_URL` environment variable if using external database

### 3. Files Included for Deployment
- ✅ `startup.py` - Main entry point for Azure
- ✅ `requirements.txt` - Python dependencies
- ✅ `web.config` - IIS configuration for Azure
- ✅ `runtime.txt` - Python version specification
- ✅ `.deployment` - Azure deployment configuration
- ✅ `azure-config.py` - Azure-specific configuration

### 4. Deployment Steps
1. Create Azure App Service (Python 3.11)
2. Configure environment variables in Azure portal
3. Deploy code via Git, GitHub Actions, or ZIP deployment
4. Monitor deployment logs in Azure portal

### 5. Post-deployment Verification
- Check application logs in Azure portal
- Verify database tables are created
- Test user registration/login
- Test project creation
- Verify AI features work (if OpenAI key configured)

### 6. Security Notes
- Never commit `.env` file with real secrets
- Use Azure Key Vault for sensitive data in production
- Enable HTTPS only in Azure App Service
- Consider enabling authentication/authorization in Azure

## Troubleshooting
- Check Application Logs in Azure portal
- Verify all environment variables are set
- Ensure Python version matches runtime.txt
- Check that all dependencies are in requirements.txt