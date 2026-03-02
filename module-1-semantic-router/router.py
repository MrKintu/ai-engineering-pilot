import os
import json
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Add parent directory to path for logger_config
sys.path.append(str(Path(__file__).parents[1]))
from logger_config import get_logger

# Set up logger
logger = get_logger(__name__)

# Load environment variables from .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

@dataclass
class RoutingConfig:
    # We use 'mini' for routing and simple tasks to keep costs near zero
    router_model: str = "gpt-4.1-nano"
    simple_task_model: str = "gpt-4o-mini"
    # We use the flagship model only for complex auditing
    complex_task_model: str = "gpt-4o"
    openai_api_key: Optional[str] = None

class RouteLayer:
    def __init__(self, config: Optional[RoutingConfig] = None) -> None:
        self.cfg = config or RoutingConfig()
        api_key = self.cfg.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)
        logger.info(f"RouteLayer initialized with router_model: {self.cfg.router_model}")

    def classify_intent(self, text: str) -> str:
        """Ask GPT-4o-mini to route the receipt."""
        logger.info(f"Classifying intent for text: {text[:50]}...")
        
        system_prompt = (
            "Classify this receipt into one of two categories:\n"
            "1. 'simple': Solo meals, coffee, fast food, under $30.\n"
            "2. 'complex': Group dinners, alcohol, steakhouse, clients, over $30.\n"
            "Respond with only the word 'simple' or 'complex'."
        )
        
        response = self.client.chat.completions.create(
            model=self.cfg.router_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0  # Keep it consistent
        )
        
        answer = response.choices[0].message.content.lower().strip()
        intent = "simple_meal" if "simple" in answer else "complex_client_dinner"
        logger.info(f"Intent classified as: {intent}")
        return intent

    def _extract_data(self, model: str, system_prompt: str, user_text: str) -> str:
        """Call OpenAI with Structured Output (JSON mode)."""
        logger.info(f"Extracting data using model: {model}")
        
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            response_format={"type": "json_object"}
        )
        
        output = response.choices[0].message.content
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

        result = {
            "intent": intent,
            "model_used": model,
            "data": json.loads(output)
        }
        
        logger.info(f"Processing completed successfully with model: {model}")
        return result


# ── Test Examples ───────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing RouteLayer with OpenAI models...")
    
    router = RouteLayer()

    # Test Case 1: Minimal info, low cost
    receipt_simple = "Starbucks, 5.20 USD, latte, 2026-01-10"

    # Test Case 2: Multi-line, high cost, higher reasoning required
    receipt_complex = (
        "The Capital Grille\nTotal: 485.60 USD\n"
        "Hosted dinner with 4 clients, 2 bottles of wine\nDate: 2026-01-15"
    )

    print("\n--- Processing Simple (via GPT-4o-mini) ---")
    print(json.dumps(router.handle(receipt_simple), indent=2))

    print("\n--- Processing Complex (via GPT-4o) ---")
    print(json.dumps(router.handle(receipt_complex), indent=2))
