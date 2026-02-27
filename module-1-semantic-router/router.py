import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv

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

    def classify_intent(self, text: str) -> str:
        """Ask GPT-4o-mini to route the receipt."""
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
        return "simple_meal" if "simple" in answer else "complex_client_dinner"

    def _extract_data(self, model: str, system_prompt: str, user_text: str) -> str:
        """Call OpenAI with Structured Output (JSON mode)."""
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def handle(self, receipt_text: str) -> Dict[str, Any]:
        intent = self.classify_intent(receipt_text)
        
        if intent == "simple_meal":
            # Path for coffee/quick lunch (Fast & Cheap)
            system_prompt = "Extract JSON: {merchant, date, total, category: 'SimpleMeal'}"
            model = self.cfg.simple_task_model
        else:
            # Path for high-stakes auditing (Highest Accuracy)
            system_prompt = (
                "You are an expert auditor. Extract JSON: "
                "{merchant, date, total, attendees, alcohol: bool, risk_flags: []}"
            )
            model = self.cfg.complex_task_model

        output = self._extract_data(model, system_prompt, receipt_text)

        return {
            "intent": intent,
            "model_used": model,
            "data": json.loads(output)
        }
