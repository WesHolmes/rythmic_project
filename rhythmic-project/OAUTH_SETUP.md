# OAuth Setup Guide for Gmail and Outlook Login

This guide will help you set up Google and Microsoft OAuth authentication for your Rhythmic application.

## Prerequisites

1. Python virtual environment activated
2. All dependencies installed (`pip install -r requirements.txt`)

## 1. Google OAuth Setup

### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.developers.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API and Google OAuth2 API

### Step 2: Configure OAuth Consent Screen
1. In the Google Cloud Console, go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type (unless you have a Google Workspace)
3. Fill in the required fields:
   - App name: "Rhythmic"
   - User support email: Your email
   - Developer contact information: Your email
4. Add scopes: `openid`, `email`, `profile`
5. Add test users (your email) if in testing mode

### Step 3: Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Web application"
4. Add authorized redirect URIs:
   - For development: `http://localhost:5000/authorize/google`
   - For production: `https://yourdomain.com/authorize/google`
5. Copy the Client ID and Client Secret

## 2. Microsoft OAuth Setup

### Step 1: Register Application in Azure
1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to "Azure Active Directory" > "App registrations"
3. Click "New registration"
4. Fill in the details:
   - Name: "Rhythmic"
   - Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: Web - `http://localhost:5000/authorize/microsoft` (for development)

### Step 2: Configure Authentication
1. In your app registration, go to "Authentication"
2. Add platform: Web
3. Add redirect URIs:
   - Development: `http://localhost:5000/authorize/microsoft`
   - Production: `https://yourdomain.com/authorize/microsoft`
4. Enable "ID tokens" and "Access tokens"
5. Save the configuration

### Step 3: Create Client Secret
1. Go to "Certificates & secrets"
2. Click "New client secret"
3. Add description and expiration
4. Copy the secret value (you won't see it again)

### Step 4: Get Application ID
1. In the app registration overview, copy the "Application (client) ID"

## 3. Environment Configuration

1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```

2. Update the `.env` file with your OAuth credentials:
   ```env
   # Flask Configuration
   SECRET_KEY=your-secret-key-change-this-in-production
   FLASK_ENV=development
   FLASK_DEBUG=True

   # Database Configuration
   DATABASE_URL=sqlite:///rhythmic.db

   # OAuth Configuration
   GOOGLE_CLIENT_ID=your-google-client-id-here
   GOOGLE_CLIENT_SECRET=your-google-client-secret-here
   OUTLOOK_CLIENT_ID=your-microsoft-client-id-here
   OUTLOOK_CLIENT_SECRET=your-microsoft-client-secret-here
   ```

## 4. Database Migration

Since we've updated the User model, you need to create a new migration:

```bash
# If you have existing data, backup your database first
cp instance/rhythmic.db instance/rhythmic.db.backup

# Delete the existing database to recreate with new schema
rm instance/rhythmic.db

# Run the application to create the new database
python app.py
```

## 5. Testing the OAuth Integration

1. Start your Flask application:
   ```bash
   python app.py
   ```

2. Navigate to `http://localhost:5000/login`

3. You should see:
   - "Continue with Google" button
   - "Continue with Microsoft" button
   - Traditional email/password form

4. Test both OAuth providers:
   - Click the Google button and complete the OAuth flow
   - Click the Microsoft button and complete the OAuth flow
   - Verify that users are created in the database with the correct provider information

## 6. Production Deployment

### For Google OAuth:
- Update the redirect URI in Google Cloud Console to your production domain
- Ensure your production domain is verified

### For Microsoft OAuth:
- Update the redirect URI in Azure Portal to your production domain
- Consider using a more restrictive account type if needed

### Environment Variables:
- Set all OAuth credentials in your production environment
- Use a strong SECRET_KEY
- Set FLASK_ENV=production and FLASK_DEBUG=False

## 7. Security Considerations

1. **HTTPS Required**: OAuth requires HTTPS in production
2. **State Parameter**: The implementation includes CSRF protection through Authlib
3. **Token Storage**: OAuth tokens are not stored - only user information
4. **Email Verification**: OAuth providers verify emails, so no additional verification needed

## 8. Troubleshooting

### Common Issues:

1. **"Invalid redirect URI"**: Check that the redirect URI in your OAuth provider matches exactly
2. **"Client ID not found"**: Verify your environment variables are set correctly
3. **"Access denied"**: Check OAuth consent screen configuration
4. **Database errors**: Ensure you've migrated the database schema

### Debug Mode:
- Set `FLASK_DEBUG=True` to see detailed error messages
- Check the Flask console for OAuth-related errors

## 9. Features Implemented

✅ Google OAuth login/logout
✅ Microsoft OAuth login/logout  
✅ User account creation via OAuth
✅ Provider-specific user identification
✅ Profile picture support (Google)
✅ Email conflict prevention
✅ Beautiful UI with OAuth buttons
✅ Secure token handling

## 10. Next Steps

Consider implementing:
- User profile management
- Account linking (connect multiple OAuth providers)
- Enhanced user information display
- OAuth token refresh (if needed for API access)
