#!/usr/bin/env python3
"""
Setup script for Rhythmic AI Assistant
This script helps set up the AI functionality for the Rhythmic project management app.
"""

import os
import sys
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import openai
        print("✅ OpenAI package is installed")
        return True
    except ImportError:
        print("❌ OpenAI package is not installed")
        return False

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    os.system("pip install -r requirements.txt")
    print("✅ Requirements installed")

def setup_environment():
    """Set up environment variables"""
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from env.example...")
        with open(env_example, 'r') as f:
            content = f.read()
        with open(env_file, 'w') as f:
            f.write(content)
        print("✅ .env file created")
        print("⚠️  Please edit .env file and add your OpenAI API key")
    elif env_file.exists():
        print("✅ .env file already exists")
    else:
        print("❌ env.example file not found")

def check_openai_key():
    """Check if OpenAI API key is configured"""
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key and api_key != 'your-openai-api-key':
        print("✅ OpenAI API key is configured")
        return True
    else:
        print("❌ OpenAI API key is not configured")
        print("Please add your OpenAI API key to the .env file")
        return False

def test_ai_connection():
    """Test AI service connection"""
    try:
        # First test OpenAI import and basic initialization
        import openai
        print(f"✅ OpenAI package version: {openai.__version__}")
        
        # Test environment variable
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY not found in environment")
            return False
        
        print(f"✅ API key found (length: {len(api_key)})")
        
        # Test OpenAI client initialization
        client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized successfully")
        
        # Test AI service
        from ai_service import AIAssistant
        ai = AIAssistant()
        print("✅ AIAssistant class initialized")
        
        # Test with a simple brief generation
        print("🧪 Testing brief generation...")
        test_brief = ai.generate_project_brief("Test Project", "This is a test project to verify AI functionality")
        
        if test_brief and 'vision' in test_brief:
            print("✅ AI service is working correctly")
            return True
        else:
            print("❌ AI service test failed - no vision in response")
            return False
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ AI service test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Rhythmic AI Assistant...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ Please run this script from the rhythmic-project directory")
        sys.exit(1)
    
    # Install requirements
    if not check_requirements():
        install_requirements()
    
    # Setup environment
    setup_environment()
    
    # Check OpenAI key
    if not check_openai_key():
        print("\n📝 To get an OpenAI API key:")
        print("1. Go to https://platform.openai.com/api-keys")
        print("2. Create a new API key")
        print("3. Add it to your .env file as OPENAI_API_KEY=your-key-here")
        print("\n⚠️  Make sure to keep your API key secure and never commit it to version control")
        return
    
    # Test AI connection
    print("\n🧪 Testing AI service...")
    if test_ai_connection():
        print("\n🎉 AI Assistant setup complete!")
        print("You can now use AI-powered features in Rhythmic:")
        print("- Generate project briefs")
        print("- Create starter project plans")
        print("- Generate AI summaries")
    else:
        print("\n❌ AI setup failed. Please check your API key and try again.")

if __name__ == "__main__":
    main()
