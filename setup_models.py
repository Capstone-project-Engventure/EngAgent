#!/usr/bin/env python3
"""
Setup script for English Learning App LLM models
Helps users choose and install appropriate models based on their system memory
"""

import subprocess
import sys
import psutil
import requests
from pathlib import Path

def get_system_memory():
    """Get available system memory in GB"""
    memory = psutil.virtual_memory()
    return memory.available / (1024**3)

def check_ollama_installed():
    """Check if Ollama is installed"""
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_ollama_model(model_name):
    """Install Ollama model"""
    print(f"Installing Ollama model: {model_name}")
    try:
        subprocess.run(['ollama', 'pull', model_name], check=True)
        print(f"✅ Successfully installed {model_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {model_name}: {e}")
        return False

def test_ollama_model(model_name):
    """Test if Ollama model works"""
    try:
        result = subprocess.run([
            'ollama', 'run', model_name, 
            'Say "Hello" in one word only'
        ], capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False

def setup_env_file():
    """Setup .env file with recommended settings"""
    env_file = Path('.env')
    env_example = Path('env.example')
    
    if env_file.exists():
        print("⚠️  .env file already exists")
        response = input("Do you want to backup and recreate it? (y/N): ")
        if response.lower() != 'y':
            return
        
        # Backup existing .env
        backup_file = Path('.env.backup')
        env_file.rename(backup_file)
        print(f"📁 Backed up existing .env to {backup_file}")
    
    # Copy from env.example
    if env_example.exists():
        content = env_example.read_text()
        env_file.write_text(content)
        print("✅ Created .env file from env.example")
    else:
        print("❌ env.example not found")

def main():
    print("🚀 English Learning App - LLM Setup")
    print("=" * 50)
    
    # Check system memory
    available_memory = get_system_memory()
    print(f"💾 Available system memory: {available_memory:.1f} GB")
    
    # Recommend models based on memory
    if available_memory < 2.0:
        recommended_model = "llama3.2:1b"
        print("⚠️  Low memory detected. Recommending small model (1.3GB)")
    elif available_memory < 4.0:
        recommended_model = "llama3.2:3b"
        print("📊 Medium memory available. Recommending medium model (2.0GB)")
    else:
        recommended_model = "mistral"
        print("🚀 High memory available. Can use large model (4.8GB)")
    
    print(f"🎯 Recommended model: {recommended_model}")
    
    # Check Ollama installation
    if not check_ollama_installed():
        print("❌ Ollama not found. Please install Ollama first:")
        print("   Visit: https://ollama.ai/download")
        return
    
    print("✅ Ollama is installed")
    
    # Setup environment file
    print("\n📝 Setting up environment configuration...")
    setup_env_file()
    
    # Ask user about model installation
    print(f"\n🤖 Model Installation")
    install_recommended = input(f"Install recommended model ({recommended_model})? (Y/n): ")
    
    if install_recommended.lower() != 'n':
        if install_ollama_model(recommended_model):
            print(f"\n🧪 Testing {recommended_model}...")
            if test_ollama_model(recommended_model):
                print("✅ Model test successful!")
            else:
                print("⚠️  Model test failed, but installation completed")
    
    # DeepSeek setup
    print(f"\n🌟 DeepSeek API Setup (Optional)")
    setup_deepseek = input("Do you want to configure DeepSeek API? (y/N): ")
    
    if setup_deepseek.lower() == 'y':
        api_key = input("Enter your DeepSeek API key: ").strip()
        if api_key:
            env_file = Path('.env')
            content = env_file.read_text()
            content = content.replace('USE_DEEPSEEK=false', 'USE_DEEPSEEK=true')
            content = content.replace('DEEPSEEK_API_KEY=your_deepseek_api_key_here', f'DEEPSEEK_API_KEY={api_key}')
            env_file.write_text(content)
            print("✅ DeepSeek API configured")
    
    print(f"\n🎉 Setup Complete!")
    print(f"📋 Summary:")
    print(f"   - System Memory: {available_memory:.1f} GB")
    print(f"   - Recommended Model: {recommended_model}")
    print(f"   - Environment file: Created/Updated")
    
    print(f"\n🚀 Next Steps:")
    print(f"   1. Start the LLM service: python -m uvicorn app.main:app --reload")
    print(f"   2. Test the health endpoint: curl http://localhost:8000/health")
    print(f"   3. Check the API docs: http://localhost:8000/docs")
    
    print(f"\n💡 Memory Optimization Tips:")
    print(f"   - Close other applications to free memory")
    print(f"   - Use smaller models if you encounter memory errors")
    print(f"   - Consider using DeepSeek API for better performance")

if __name__ == "__main__":
    main() 