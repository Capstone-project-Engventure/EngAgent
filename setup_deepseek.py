#!/usr/bin/env python3
"""
DeepSeek API Setup Script
Automated setup and testing for DeepSeek integration
"""

import os
import sys
import requests
import json
from pathlib import Path
import time

def print_header():
    print("🌟" * 25)
    print("🚀 DEEPSEEK API SETUP")
    print("🌟" * 25)
    print()

def check_requirements():
    """Check if required packages are installed"""
    try:
        import requests
        import dotenv
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False

def get_api_key():
    """Get API key from user"""
    print("🔑 DeepSeek API Key Setup")
    print("=" * 30)
    print("1. Visit: https://platform.deepseek.com")
    print("2. Sign up/Login")
    print("3. Go to 'API Keys' section")
    print("4. Create new API key")
    print("5. Copy the key (starts with 'sk-')")
    print()
    
    while True:
        api_key = input("🔐 Paste your DeepSeek API key: ").strip()
        
        if not api_key:
            print("❌ Please enter an API key")
            continue
            
        if not api_key.startswith('sk-'):
            print("❌ DeepSeek API key should start with 'sk-'")
            continue
            
        if len(api_key) < 20:
            print("❌ API key seems too short")
            continue
            
        return api_key

def test_api_key(api_key):
    """Test if API key works"""
    print("\n🧪 Testing API key...")
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    data = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'user', 'content': 'Say "Hello" in one word only'}
        ],
        'max_tokens': 10
    }
    
    try:
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            usage = result['usage']
            
            print("✅ API key works!")
            print(f"📝 Response: {message}")
            print(f"📊 Tokens used: {usage['total_tokens']}")
            return True
            
        elif response.status_code == 401:
            print("❌ API key is invalid")
            return False
            
        elif response.status_code == 429:
            print("⚠️ Rate limit exceeded, but API key is valid")
            return True
            
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False

def update_env_file(api_key):
    """Update .env file with DeepSeek configuration"""
    env_file = Path('.env')
    
    # Read existing .env or create new
    if env_file.exists():
        content = env_file.read_text()
    else:
        # Copy from env.example if exists
        env_example = Path('env.example')
        if env_example.exists():
            content = env_example.read_text()
        else:
            content = ""
    
    # Update DeepSeek configuration
    deepseek_config = f"""
# DeepSeek Configuration (Added by setup_deepseek.py)
USE_DEEPSEEK=true
DEEPSEEK_API_KEY={api_key}
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
"""
    
    # Remove existing DeepSeek config if any
    lines = content.split('\n')
    filtered_lines = []
    skip_until_blank = False
    
    for line in lines:
        if 'DeepSeek Configuration' in line:
            skip_until_blank = True
            continue
        elif skip_until_blank and line.strip() == '':
            skip_until_blank = False
            continue
        elif skip_until_blank:
            continue
        elif line.startswith('USE_DEEPSEEK=') or line.startswith('DEEPSEEK_'):
            continue
        else:
            filtered_lines.append(line)
    
    # Add new config
    new_content = '\n'.join(filtered_lines).rstrip() + deepseek_config
    
    # Write back to file
    env_file.write_text(new_content)
    print(f"✅ Updated {env_file}")

def test_app_integration():
    """Test DeepSeek integration in the app"""
    print("\n🔧 Testing app integration...")
    
    try:
        # Test configuration loading
        sys.path.append('.')
        from app.core.config import settings
        
        print(f"📋 DeepSeek enabled: {settings.use_deepseek}")
        print(f"🔑 API key configured: {bool(settings.deepseek_api_key)}")
        print(f"🤖 Model: {settings.deepseek_model}")
        
        if not settings.use_deepseek:
            print("❌ USE_DEEPSEEK is not true")
            return False
            
        if not settings.deepseek_api_key:
            print("❌ API key not loaded")
            return False
            
        print("✅ Configuration loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def check_balance(api_key):
    """Check account balance"""
    print("\n💰 Checking account balance...")
    
    headers = {'Authorization': f'Bearer {api_key}'}
    
    try:
        # Try to get usage info (this endpoint might not exist, it's for demo)
        response = requests.get(
            'https://api.deepseek.com/dashboard/billing/subscription',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            balance = data.get('hard_limit_usd', 'unknown')
            print(f"💳 Account balance: ${balance}")
        else:
            print("💡 Check your balance at: https://platform.deepseek.com/usage")
            
    except Exception:
        print("💡 Check your balance at: https://platform.deepseek.com/usage")

def generate_test_commands():
    """Generate test commands for user"""
    print("\n🚀 Test Commands")
    print("=" * 20)
    
    commands = [
        "# 1. Start the application",
        "python -m uvicorn app.main:app --reload",
        "",
        "# 2. Test health check (in another terminal)",
        "curl http://localhost:8000/health",
        "",
        "# 3. Test DeepSeek generation",
        'curl -X POST "http://localhost:8000/api/exercises/no-rag?modelType=deepseek" \\',
        '  -H "Content-Type: application/json" \\',
        '  -d \'{"prompt_name": "english_exercise_default", "number": 2, "type": "mcq", "skill": "vocabulary", "level": "beginner", "topic": "animals"}\'',
        "",
        "# 4. Test with RAG",
        'curl -X POST "http://localhost:8000/api/exercises/native-rag?modelType=deepseek" \\',
        '  -H "Content-Type: application/json" \\',
        '  -d \'{"prompt_name": "english_exercise_default", "number": 3, "type": "mcq", "skill": "grammar", "level": "intermediate", "topic": "present perfect"}\''
    ]
    
    for cmd in commands:
        print(cmd)

def main():
    print_header()
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Get API key
    api_key = get_api_key()
    
    # Test API key
    if not test_api_key(api_key):
        print("\n❌ API key test failed. Please check:")
        print("1. API key is correct")
        print("2. Account has sufficient balance")
        print("3. Internet connection")
        sys.exit(1)
    
    # Check balance
    check_balance(api_key)
    
    # Update .env file
    print("\n📝 Updating configuration...")
    update_env_file(api_key)
    
    # Test app integration
    if test_app_integration():
        print("\n🎉 Setup completed successfully!")
    else:
        print("\n⚠️ Setup completed but with configuration warnings")
    
    # Generate test commands
    generate_test_commands()
    
    print("\n" + "🌟" * 25)
    print("💡 NEXT STEPS:")
    print("1. Run the test commands above")
    print("2. Visit: https://platform.deepseek.com/usage to monitor usage")
    print("3. Check: MEMORY_OPTIMIZATION_GUIDE.md for more tips")
    print("🌟" * 25)

if __name__ == "__main__":
    main() 