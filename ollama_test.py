import os
import requests
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    base_url = os.getenv("OLLAMA_BASE_URL")
    model = os.getenv("OLLAMA_MODEL")
    
    if not base_url:
        print("Error: OLLAMA_BASE_URL not found in environment variables.")
        print("Please ensure you have a .env file with OLLAMA_BASE_URL set.")
        return
    
    print(f"Initializing Ollama client at {base_url}...")
    print(f"Using model: {model}")
    
    try:
        # Test Ollama connection and model availability
        print(f"Sending test request to Ollama ({model})...")
        
        # First, check if Ollama is running and model is available
        tags_response = requests.get(f"{base_url}/api/tags", timeout=10)
        if tags_response.status_code == 200:
            models = [m["name"] for m in tags_response.json().get("models", [])]
            if model in models:
                print(f"✅ Model {model} is available")
            else:
                print(f"⚠️  Model {model} not found. Available models: {', '.join(models[:5])}")
                return
        else:
            print(f"❌ Failed to connect to Ollama at {base_url}")
            print("Please ensure Ollama is running: ollama serve")
            return
        
        # Test generation capability
        payload = {
            "model": model,
            "prompt": "Hello! This is a test call. Please respond with a short confirmation.",
            "stream": False
        }
        
        response = requests.post(f"{base_url}/api/generate", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("response", "")
            print(f"\n✅ Success! Ollama responded: \n\"{content}\"")
            print(f"Response metadata: model={data.get('model')}, done={data.get('done')}")
        else:
            print(f"❌ Generation request failed with status {response.status_code}")
            print(f"Response: {response.text}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error during Ollama API call: {e}")
    except Exception as e:
        print(f"❌ An error occurred during the API call: {e}")

def check_embedding_model_availability(base_url: str, embed_model: str) -> bool:
    """Check if the embedding model is available in Ollama."""
    try:
        tags_response = requests.get(f"{base_url}/api/tags", timeout=10)
        if tags_response.status_code == 200:
            models = [m["name"] for m in tags_response.json().get("models", [])]
            if embed_model not in models:
                print(f"⚠️  Embedding model {embed_model} not found. Available models: {', '.join(models[:5])}")
                print("   You may need to pull it: ollama pull embeddinggemma")
                return False
            else:
                print(f"✅ Embedding model {embed_model} is available")
                return True
        else:
            print(f"❌ Failed to check available models: {tags_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking model availability: {e}")
        return False


def parse_embedding_response(data: dict) -> tuple[bool, list[float] | None]:
    """Parse different Ollama embedding response formats."""
    print(f"Embedding response structure: {list(data.keys())}")
    
    # Handle different Ollama embedding response formats
    if "embeddings" in data and len(data["embeddings"]) > 0:
        embedding = data["embeddings"][0]
        if "embedding" in embedding:
            return True, embedding["embedding"]
        else:
            print("⚠️  Embedding response format unexpected")
            print(f"Available keys: {list(embedding.keys())}")
            return False, None
    elif "embedding" in data:
        return True, data["embedding"]
    else:
        print("⚠️  No embedding data found in response")
        print(f"Response keys: {list(data.keys())}")
        return False, None


def test_embedding_endpoint():
    """Test the embedding endpoint if available."""
    base_url = os.getenv("OLLAMA_BASE_URL")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL")
    
    print(f"\n🧪 Testing embedding endpoint with {embed_model}...")
    
    # Check model availability first
    if not check_embedding_model_availability(base_url, embed_model):
        return
    
    try:
        payload = {
            "model": embed_model,
            "prompt": "This is a test for embedding generation."
        }
        
        response = requests.post(f"{base_url}/api/embeddings", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            success, embed_vector = parse_embedding_response(data)
            
            if success and embed_vector:
                print("✅ Embedding generated successfully!")
                print(f"Embedding dimensions: {len(embed_vector)}")
                print(f"First 5 values: {embed_vector[:5]}")
        else:
            print(f"❌ Embedding request failed with status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")

if __name__ == "__main__":
    print("🦙 Ollama API Test Suite")
    print("=" * 40)
    
    main()
    test_embedding_endpoint()
    
    print("\n" + "=" * 40)
    print("🎯 Test completed!")
    print("\n💡 Tips:")
    print("   - Ensure Ollama is running: ollama serve")
    print("   - Pull required models: ollama pull gemma3")
    print("   - Check environment variables in .env file")
