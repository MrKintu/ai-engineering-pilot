#!/usr/bin/env python3
"""
Test script for Capstone OCR with realistic receipt image
"""

import base64
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parents[1]))

# Load environment variables
load_dotenv()

from capstone_core2 import CapstoneEngine
from logger_config import get_logger

logger = get_logger(__name__)

def create_test_receipt_image():
    """Create a simple receipt image using PIL."""
    # Create a white image with receipt dimensions
    width, height = 400, 600
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a basic font, fallback to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        title_font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        raise
    
    # Draw receipt content
    y_position = 30
    
    # Store name
    draw.text((50, y_position), "COFFEE SHOP", fill='black', font=title_font)
    y_position += 40
    
    # Store info
    draw.text((50, y_position), "123 Main Street", fill='black', font=font)
    y_position += 25
    draw.text((50, y_position), "New York, NY 10001", fill='black', font=font)
    y_position += 25
    draw.text((50, y_position), "Tel: (555) 123-4567", fill='black', font=font)
    y_position += 40
    
    # Date and time
    draw.text((50, y_position), "Date: 2026-03-02", fill='black', font=font)
    y_position += 25
    draw.text((50, y_position), "Time: 14:30 PM", fill='black', font=font)
    y_position += 40
    
    # Draw line
    draw.line([(50, y_position), (350, y_position)], fill='black', width=2)
    y_position += 30
    
    # Items
    items = [
        ("Large Coffee", 1, 4.50),
        ("Croissant", 1, 3.25),
        ("Bagel", 2, 2.00),
    ]
    
    for item_name, quantity, price in items:
        draw.text((50, y_position), item_name, fill='black', font=font)
        draw.text((250, y_position), f"{quantity}", fill='black', font=font)
        draw.text((300, y_position), f"${price:.2f}", fill='black', font=font)
        y_position += 30
    
    # Draw line
    y_position += 20
    draw.line([(50, y_position), (350, y_position)], fill='black', width=2)
    y_position += 30
    
    # Total
    subtotal = sum(price * qty for _, qty, price in items)
    tax = subtotal * 0.08  # 8% tax
    total = subtotal + tax
    
    draw.text((250, y_position), "Subtotal:", fill='black', font=font)
    draw.text((300, y_position), f"${subtotal:.2f}", fill='black', font=font)
    y_position += 25
    
    draw.text((250, y_position), "Tax:", fill='black', font=font)
    draw.text((300, y_position), f"${tax:.2f}", fill='black', font=font)
    y_position += 25
    
    draw.text((250, y_position), "Total:", fill='black', font=title_font)
    draw.text((300, y_position), f"${total:.2f}", fill='black', font=title_font)
    y_position += 40
    
    # Thank you message
    draw.text((150, y_position), "Thank You!", fill='black', font=title_font)
    y_position += 30
    draw.text((100, y_position), "Please Come Again", fill='black', font=font)
    
    return img

def test_ocr_with_realistic_image():
    """Test OCR functionality with a realistic receipt image."""
    print("🧪 Testing Capstone OCR with Realistic Receipt Image...")
    print("=" * 60)
    
    # Create test image
    print("📸 Creating test receipt image...")
    img = create_test_receipt_image()
    
    # Save image for debugging
    img.save("test_receipt.png")
    print("✅ Test image saved as 'test_receipt.png'")
    
    # Convert to bytes
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    image_bytes = buffer.getvalue()
    
    print(f"📏 Image size: {len(image_bytes)} bytes")
    print(f"📐 Image dimensions: {img.size}")
    
    # Initialize capstone engine
    print("\n🚀 Initializing Capstone Engine...")
    engine = CapstoneEngine()
    
    # Test different backends
    backends = ["auto", "ollama", "openai"]
    
    for backend in backends:
        print(f"\n🔍 Testing backend: {backend}")
        print("-" * 40)
        
        try:
            # Test extraction
            result = engine.extract_text_from_image(
                image_bytes=image_bytes,
                mime_type="image/png",
                backend=backend
            )
            
            if result["ok"]:
                print(f"✅ {backend.title()} extraction successful!")
                print(f"   Backend used: {result.get('backend', 'unknown')}")
                print(f"   Model: {result.get('model', 'unknown')}")
                print(f"   Text length: {len(result.get('text', ''))} characters")
                print("   Extracted text:")
                print("   " + "="*40)
                for line in result.get('text', '').split('\n'):
                    if line.strip():
                        print(f"   {line}")
                print("   " + "="*40)
            else:
                print(f"❌ {backend.title()} extraction failed:")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                
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

def main():
    """Run all tests."""
    print("🚀 Capstone OCR Realistic Image Test Suite")
    print("=" * 60)
    
    # Test environment setup
    test_environment_setup()
    
    # Test with realistic image
    test_ocr_with_realistic_image()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("✅ Environment configuration checked")
    print("✅ Realistic receipt image created")
    print("✅ OCR backends tested with proper image")
    
    print("\n💡 Next Steps:")
    print("  - Check the extracted text above for accuracy")
    print("  - Test with real receipt images for better results")
    print("  - Adjust Ollama model if needed for better OCR quality")
    print("  - The test image 'test_receipt.png' is available for debugging")

if __name__ == "__main__":
    main()
