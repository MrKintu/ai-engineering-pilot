#!/usr/bin/env python3
"""
Test script for Ollama Vision functionality in receipt_extractor2.py
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

OLLAMA_BASE_URL = env.get("OLLAMA_BASE_URL")
OLLAMA_MODEL = env.get("OLLAMA_MODEL")
OLLAMA_VISION_MODEL = env.get("OLLAMA_VISION_MODEL")

from receipt_extractor2 import ReceiptExtractorOllama
from logger_config import get_logger

logger = get_logger(__name__)

def test_text_extraction():
    """Test text-based receipt extraction."""
    print("🧪 Testing Text Extraction with Ollama...")
    
    extractor = ReceiptExtractorOllama(
        model=OLLAMA_MODEL, 
        vision_model=OLLAMA_VISION_MODEL, 
        max_retries=3
    )
    
    messy_ocr = """
    SNAPMART GROCERY
    2026/01/17
    ---
    Milk 3.99
    Bread 2.50
    Eggs 4.25
    ---
    Subtotal  $10.74
    TAX 0.86
    TOTAL $11.60
    Thank you for shopping!
    """
    
    try:
        receipt = extractor.extract(messy_ocr)
        print("✅ Text extraction successful:")
        print(f"  Merchant: {receipt.merchant}")
        print(f"  Date: {receipt.date}")
        print(f"  Total: {receipt.total} {receipt.currency}")
        print(f"  Category: {receipt.category}")
        if receipt.tax:
            print(f"  Tax: {receipt.tax} {receipt.currency}")
        return True
    except Exception as e:
        print(f"❌ Text extraction failed: {e}")
        return False

def test_vision_extraction():
    """Test image-based receipt extraction."""
    print("\n🧪 Testing Vision Extraction with Ollama...")
    
    extractor = ReceiptExtractorOllama(
        model=OLLAMA_MODEL, 
        vision_model=OLLAMA_VISION_MODEL, 
        max_retries=3
    )
    
    # Check if we have a test image
    test_image_path = Path("test_receipt.png")
    if not test_image_path.exists():
        print("⚠️  No test image found. Skipping vision test.")
        print("   To test vision, place a receipt image as 'test_receipt.png' in this directory.")
        return True
    
    try:
        with open(test_image_path, "rb") as f:
            image_bytes = f.read()
        
        receipt = extractor.extract_from_image(image_bytes, mime_type="image/png")
        print("✅ Vision extraction successful:")
        print(f"  Merchant: {receipt.merchant}")
        print(f"  Date: {receipt.date}")
        print(f"  Total: {receipt.total} {receipt.currency}")
        print(f"  Category: {receipt.category}")
        if receipt.tax:
            print(f"  Tax: {receipt.tax} {receipt.currency}")
        return True
    except Exception as e:
        print(f"❌ Vision extraction failed: {e}")
        return False

def _get_ollama_models(base_url: str) -> tuple[bool, list[str]]:
    """Get available models from Ollama."""
    try:
        import requests
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            return True, model_names
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            return False, []
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("   Make sure Ollama is running: ollama serve")
        return False, []

def _get_required_models() -> list[str]:
    """Get required models from environment variables or defaults."""
    required_models = []
    if OLLAMA_MODEL:
        required_models.append(OLLAMA_MODEL)
    if OLLAMA_VISION_MODEL:
        required_models.append(OLLAMA_VISION_MODEL)
    
    # Use defaults if environment variables are not set
    if not required_models:
        required_models = ["gemma3:latest", "llava:latest"]
    
    return required_models

def _check_model_availability(model_names: list[str], required_models: list[str]) -> bool:
    """Check if required models are available and provide feedback."""
    missing_models = [m for m in required_models if m not in model_names]
    
    if missing_models:
        print(f"⚠️  Missing models: {', '.join(missing_models)}")
        print("Pull them with:")
        for model in missing_models:
            print(f" ollama pull {model}")
        return False
    else:
        print("✅ All required models are available")
        print(f"Using text model: {OLLAMA_MODEL}")
        print(f"Using vision model: {OLLAMA_VISION_MODEL}")
        return True

def check_ollama_status() -> bool:
    """Check if Ollama is running and models are available."""
    print("🔍 Checking Ollama status...")
    
    # Use environment variable for base URL or default
    base_url = OLLAMA_BASE_URL
    
    # Get available models
    success, model_names = _get_ollama_models(base_url)
    if not success:
        return False
    
    print("✅ Ollama is running")
    print(f"   Available models: {', '.join(model_names[:5])}")
    
    # Get required models
    required_models = _get_required_models()
    
    # Check model availability
    return _check_model_availability(model_names, required_models)

def main():
    """Run all tests."""
    print("🚀 Ollama Vision Receipt Extractor Test Suite")
    print("=" * 50)
    
    # Check Ollama status first
    if not check_ollama_status():
        print("\n❌ Please fix Ollama setup before running tests.")
        return
    
    # Run tests
    text_success = test_text_extraction()
    vision_success = test_vision_extraction()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  Text Extraction: {'✅ PASS' if text_success else '❌ FAIL'}")
    print(f"  Vision Extraction: {'✅ PASS' if vision_success else '❌ FAIL'}")
    
    if text_success and vision_success:
        print("\n🎉 All tests passed! Your local vision extractor is working perfectly.")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")
    
    print("\n💡 Usage Tips:")
    print("  - Start Ollama: ollama serve")
    print("  - Pull models: ollama pull gemma3:latest && ollama pull llava:latest")
    print("  - Configure environment variables in .env:")
    print(f"    OLLAMA_BASE_URL={OLLAMA_BASE_URL}")
    print(f"    OLLAMA_MODEL={OLLAMA_MODEL}")
    print(f"    OLLAMA_VISION_MODEL={OLLAMA_VISION_MODEL}")
    print("  - Run Streamlit: uv run streamlit run streamlit_app.py")

if __name__ == "__main__":
    main()
