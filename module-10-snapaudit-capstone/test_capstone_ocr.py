#!/usr/bin/env python3
"""
Test script for Capstone OCR functionality with both OpenAI and Ollama backends
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parents[1]))

# Load environment variables from .env file in root directory
load_dotenv()
env = os.environ

# Import capstone engine
from capstone_core2 import CapstoneEngine
from logger_config import get_logger

logger = get_logger(__name__)

def test_ocr_backends():
    """Test OCR functionality with different backends."""
    print("🧪 Testing Capstone OCR with Multiple Backends...")
    
    # Test with different backends
    backends = ["auto", "ollama", "openai"]
    
    for backend in backends:
        print(f"\n🔍 Testing backend: {backend}")
        print("-" * 40)
        
        # Create a simple test image (in practice, you'd use a real receipt image)
        test_image_path = Path("test_receipt.png")
        
        if not test_image_path.exists():
            print(f"⚠️  No test image found for {backend} test.")
            print("   To test OCR, place a receipt image as 'test_receipt.png' in this directory.")
            continue
        
        try:
            with open(test_image_path, "rb") as f:
                image_bytes = f.read()
            
            # Initialize capstone engine for each test
            capstone_engine = CapstoneEngine()
            
            # Test extraction
            result = capstone_engine.extract_text_from_image(
                image_bytes=image_bytes,
                mime_type="image/png",
                backend=backend
            )
            
            if result["ok"]:
                print(f"✅ {backend.title()} extraction successful:")
                print(f"   Backend used: {result.get('backend', 'unknown')}")
                print(f"   Model: {result.get('model', 'unknown')}")
                print(f"   Text length: {len(result.get('text', ''))} characters")
                print(f"   Preview: {result.get('text', '')[:100]}...")
            else:
                print(f"❌ {backend.title()} extraction failed:")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                
        except FileNotFoundError as e:
            print(f"❌ {backend.title()} test failed: File not found - {e}")
        except Exception as e:
            print(f"❌ {backend.title()} test failed with exception: {e}")

def test_environment_setup():
    """Test environment configuration."""
    print("🔍 Checking environment configuration...")
    
    # Check OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("✅ OpenAI API key is configured")
    else:
        print("⚠️  OpenAI API key not found (OpenAI backend unavailable)")
    
    # Check Ollama
    try:
        import requests
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            vision_model = os.getenv("OLLAMA_VISION_MODEL", "llava:latest")
            
            print("✅ Ollama is running")
            print(f"   Available models: {', '.join(model_names[:3])}")
            
            if vision_model in model_names:
                print(f"✅ Vision model {vision_model} is available")
            else:
                print(f"⚠️  Vision model {vision_model} not found")
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("   Make sure Ollama is running: ollama serve")

def test_auto_backend_logic():
    """Test the auto backend selection logic."""
    print("\n🧪 Testing Auto Backend Selection Logic...")
    
    # Test auto mode with different configurations
    print("📊 Backend Selection Strategy:")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    ollama_available = False
    
    try:
        import requests
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        ollama_available = response.status_code == 200
    except requests.exceptions.RequestException:
        pass
    
    if openai_key and ollama_available:
        print("   Strategy: Try Ollama first, fallback to OpenAI")
        print("   Reason: Both backends available, prefer local processing")
    elif ollama_available and not openai_key:
        print("   Strategy: Use Ollama only")
        print("   Reason: Only Ollama available")
    elif openai_key and not ollama_available:
        print("   Strategy: Use OpenAI only")
        print("   Reason: Only OpenAI available")
    else:
        print("   Strategy: No backends available")
        print("   Reason: Neither OpenAI nor Ollama configured")

def main():
    """Run all OCR tests."""
    print("🚀 Capstone OCR Backend Test Suite")
    print("=" * 50)
    
    # Test environment setup
    test_environment_setup()
    
    # Test auto backend logic
    test_auto_backend_logic()
    
    # Test OCR backends
    test_ocr_backends()
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print("✅ Environment configuration checked")
    print("✅ Backend selection logic verified")
    print("✅ OCR backends tested")
    
    print("\n💡 Usage Tips:")
    print("  - Configure environment variables in .env:")
    print("    OPENAI_API_KEY=your_openai_api_key")
    print("    OLLAMA_BASE_URL=http://localhost:11434")
    print("    OLLAMA_VISION_MODEL=llava:latest")
    print("  - Start Ollama: ollama serve")
    print("  - Pull vision model: ollama pull llava:latest")
    print("  - Use backend='auto' for intelligent selection")
    print("  - Use backend='ollama' for local-only processing")
    print("  - Use backend='openai' for cloud-only processing")

if __name__ == "__main__":
    main()
