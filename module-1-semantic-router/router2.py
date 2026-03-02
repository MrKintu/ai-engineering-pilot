import os
import json
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for logger_config
sys.path.append(str(Path(__file__).parents[1]))
from logger_config import get_logger

# Set up logger
logger = get_logger(__name__)

try:
    from ollama import Client as OllamaClient
except ImportError:
    print("Error: ollama package is required. Install with: pip install ollama")
    exit(1)

# Load environment variables from .env file in root directory
load_dotenv()
env = os.environ
OLLAMA_MODEL = env.get("OLLAMA_MODEL")

@dataclass
class RoutingConfig:
    # Using local Ollama model for all operations
    router_model: str = OLLAMA_MODEL
    simple_task_model: str = OLLAMA_MODEL
    complex_task_model: str = OLLAMA_MODEL
    ollama_base_url: str = env.get("OLLAMA_BASE_URL")

class RouteLayer:
    def __init__(self, config: Optional[RoutingConfig] = None) -> None:
        self.cfg = config or RoutingConfig()
        self.client = OllamaClient(host=self.cfg.ollama_base_url)
        logger.info(f"RouteLayer initialized with Ollama model: {self.cfg.router_model}")

    def classify_intent(self, text: str) -> str:
        """Route the receipt using configured model."""
        logger.info(f"Classifying intent for text: {text[:50]}...")
        
        system_prompt = (
            "Classify this receipt into one of two categories:\n"
            "1. 'simple': Solo meals, coffee, fast food, under $30.\n"
            "2. 'complex': Group dinners, alcohol, steakhouse, clients, over $30.\n"
            "Respond with only the word 'simple' or 'complex'."
        )
        
        response = self.client.chat(
            model=self.cfg.router_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            options={"temperature": 0}
        )
        answer = response["message"]["content"].lower().strip()
        
        intent = "simple_meal" if "simple" in answer else "complex_client_dinner"
        logger.info(f"Intent classified as: {intent}")
        return intent

    def _clean_json_output(self, output: str) -> str:
        """Clean JSON output by removing markdown code blocks and extra whitespace."""
        logger.debug(f"Cleaning JSON output: {output[:100]}...")
        
        output = output.strip()
        
        # Remove markdown code blocks if present
        if output.startswith('```json'):
            output = output[7:]  # Remove ```json
        elif output.startswith('```'):
            output = output[3:]   # Remove ```
            
        if output.endswith('```'):
            output = output[:-3]  # Remove closing ```
            
        cleaned = output.strip()
        logger.debug(f"Cleaned JSON output: {cleaned[:100]}...")
        return cleaned

    def _extract_data(self, model: str, system_prompt: str, user_text: str) -> str:
        """Call Ollama model for data extraction."""
        logger.info(f"Extracting data using model: {model}")
        
        # For Ollama, we need to explicitly request JSON format in the prompt
        json_system_prompt = f"{system_prompt}\n\nIMPORTANT: Respond with valid JSON only, no other text."
        response = self.client.chat(
            model=model,
            messages=[
                {"role": "system", "content": json_system_prompt},
                {"role": "user", "content": user_text}
            ],
            options={"temperature": 0}
        )
        
        output = response["message"]["content"].strip()
        logger.info(f"Raw extraction output: {output}")
        return output

    def handle(self, receipt_text: str) -> Dict[str, Any]:
        logger.info(f"Processing receipt: {receipt_text[:50]}...")
        
        intent = self.classify_intent(receipt_text)
        
        if intent == "simple_meal":
            # Path for coffee/quick lunch (Fast & Cheap)
            system_prompt = "Extract JSON: {merchant, date, total, category: 'SimpleMeal'}"
            model = self.cfg.simple_task_model
            logger.info("Using simple meal extraction path")
        else:
            # Path for high-stakes auditing (Highest Accuracy)
            system_prompt = (
                "You are an expert auditor. Extract JSON: "
                "{merchant, date, total, attendees, alcohol: bool, risk_flags: []}"
            )
            model = self.cfg.complex_task_model
            logger.info("Using complex client dinner extraction path")

        output = self._extract_data(model, system_prompt, receipt_text)

        # Parse JSON with error handling
        try:
            # Clean the output by removing markdown code blocks if present
            cleaned_output = self._clean_json_output(output)
            parsed_data = json.loads(cleaned_output)
            logger.info("JSON parsing successful")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from model output: {e}")
            logger.error(f"Raw output: {repr(output)}")
            # Fallback: create a basic structure
            parsed_data = {
                "error": "Failed to parse JSON",
                "raw_output": output,
                "merchant": "Unknown",
                "total": 0.0
            }

        result = {
            "intent": intent,
            "model_used": model,
            "data": parsed_data
        }
        
        logger.info(f"Processing completed successfully with model: {model}")
        return result

# --- Testing Block ---
if __name__ == "__main__":
    # Use Gemma3 for all operations
    config = RoutingConfig(
        router_model=OLLAMA_MODEL,
        simple_task_model=OLLAMA_MODEL,
        complex_task_model=OLLAMA_MODEL
    )
    
    router = RouteLayer(config)

    # Test Case 1: Minimal info, low cost
    receipt_simple = "Starbucks, 5.20 USD, latte, 2026-01-10"

    # Test Case 2: Multi-line, high cost, higher reasoning required
    receipt_complex = (
        "The Capital Grille\nTotal: 485.60 USD\n"
        "Hosted dinner with 4 clients, 2 bottles of wine\nDate: 2026-01-15"
    )

    print("\n--- Processing Simple (via Gemma3) ---")
    print(json.dumps(router.handle(receipt_simple), indent=2))

    print("\n--- Processing Complex (via Gemma3) ---")
    print(json.dumps(router.handle(receipt_complex), indent=2))
