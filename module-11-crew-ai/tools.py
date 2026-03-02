from typing import List, Dict, Any, Optional, Callable
import requests
import os
import sys
from pathlib import Path

# Import centralized logging configuration
sys.path.append(str(Path(__file__).resolve().parents[1]))
from logger_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)

# --- Retriever adapter (wraps your existing hybrid retriever) ---
class RetrieverTool:
    """
    Thin adapter to your hybrid retriever.
    Expects an object with a `search(query, top_k)` method that returns (chunk, score) tuples.
    """

    def __init__(self, retriever: Any):
        logger.debug("Initializing RetrieverTool")
        self.retriever = retriever

    def __call__(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        logger.debug(f"RetrieverTool searching for: '{query}' with top_k={top_k}")
        results = self.retriever.search(query, top_k=top_k)
        # Normalize to simple dicts
        normalized_results = [
            {
                "chunk_id": r[0].chunk_id,
                "text": r[0].text,
                "section": r[0].section_number,
                "score": float(r[1]) if r[1] is not None else None,
            }
            for r in results
        ]
        logger.info(f"RetrieverTool found {len(normalized_results)} results")
        return normalized_results

# --- Ollama generator adapter ---
class OllamaGenerator:
    """
    Minimal Ollama text generation wrapper.
    Requires OLLAMA_BASE_URL and OLLAMA_MODEL env vars.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL")
        self.model = model or os.getenv("OLLAMA_MODEL")
        self.endpoint = f"{self.base_url}/api/generate"
        logger.info(f"OllamaGenerator initialized with model: {self.model} at {self.base_url}")

    def __call__(self, prompt: str, max_tokens: int = 512) -> str:
        logger.debug(f"OllamaGenerator generating response for prompt: {prompt[:50]}...")
        payload = {"model": self.model, "prompt": prompt, "max_tokens": max_tokens, "stream": False}
        
        try:
            resp = requests.post(self.endpoint, json=payload, timeout=60)
            logger.debug(f"Ollama response status: {resp.status_code}")
            
            resp.raise_for_status()
            
            # Parse the JSON response
            data = resp.json()
            logger.debug(f"Parsed JSON keys: {list(data.keys())}")
            
            text = self._extract_text_from_response(data)
            logger.info(f"OllamaGenerator generated {len(text)} characters")
            return text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OllamaGenerator request failed: {e}")
            raise ConnectionError(f"Failed to connect to Ollama at {self.base_url}: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"OllamaGenerator JSON decode failed: {e}")
            raise ValueError(f"Invalid JSON response from Ollama: {e}")
        except Exception as e:
            logger.error(f"OllamaGenerator failed: {e}")
            raise

    def _extract_text_from_response(self, data: dict) -> str:
        """Extract text from various Ollama response formats."""
        # Try standard Ollama response format
        if "response" in data:
            return data["response"]
        elif "text" in data:
            return data["text"]
        elif "output" in data:
            return data["output"]
        elif "result" in data:
            return data["result"]
        elif "content" in data:
            return data["content"]
        elif "message" in data and "content" in data["message"]:
            return data["message"]["content"]
        elif "choices" in data:
            return self._extract_from_choices(data["choices"])
        elif isinstance(data, str):
            return data
        else:
            # Debug: log the actual response structure
            logger.warning(f"Unexpected Ollama response format: {list(data.keys())}")
            logger.debug(f"Full response: {data}")
            return ""

    def _extract_from_choices(self, choices: list) -> str:
        """Extract text from OpenAI-style choices."""
        text = ""
        if not isinstance(choices, list):
            return text
            
        for choice in choices:
            if "text" in choice:
                text += choice["text"]
            elif "message" in choice and "content" in choice["message"]:
                text += choice["message"]["content"]
            elif "delta" in choice and "content" in choice["delta"]:
                text += choice["delta"]["content"]
        return text

# --- Simple logger tool ---
def logger_tool(message: str) -> None:
    logger.info("LoggerTool: %s", message)
