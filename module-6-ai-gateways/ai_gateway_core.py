from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for logger_config
sys.path.append(str(Path(__file__).parents[1]))
from logger_config import get_logger

# Set up logger
logger = get_logger(__name__)


@dataclass
class ModelEndpoint:
    provider: str
    model: str
    cost_per_1k_tokens: Decimal
    tier: str  # cheap, balanced, premium
    healthy: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "cost_per_1k_tokens": str(self.cost_per_1k_tokens),
            "tier": self.tier,
            "healthy": self.healthy,
        }


@dataclass
class GatewayResponse:
    ok: bool
    provider: str
    model: str
    reason: str
    tokens: int
    estimated_cost_usd: Decimal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "provider": self.provider,
            "model": self.model,
            "reason": self.reason,
            "tokens": self.tokens,
            "estimated_cost_usd": str(self.estimated_cost_usd),
        }


class RequestClassifier:
    """Classify receipt complexity for routing decisions."""

    SIMPLE_HINTS = {"coffee", "taxi", "rideshare", "parking", "snack"}
    COMPLEX_HINTS = {"client dinner", "international", "first class", "multi-attendee", "vp exception"}

    def classify(self, receipt: Dict[str, Any]) -> str:
        category = str(receipt.get("category", "")).lower()
        note = str(receipt.get("note", "")).lower()
        total = Decimal(str(receipt.get("total", 0)))

        text = f"{category} {note}"

        if any(hint in text for hint in self.COMPLEX_HINTS) or total >= Decimal("150"):
            return "complex"
        if any(hint in text for hint in self.SIMPLE_HINTS) or total <= Decimal("30"):
            return "simple"
        return "moderate"


class AIGateway:
    """Centralized AI gateway with smart routing + fallback."""

    def __init__(self):
        self.classifier = RequestClassifier()
        self.endpoints: List[ModelEndpoint] = [
            ModelEndpoint("openai", "gpt-4o-mini", Decimal("0.60"), "premium", healthy=True),
            ModelEndpoint("azure", "gpt-4o-mini", Decimal("0.65"), "premium", healthy=True),
            ModelEndpoint("anthropic", "claude-3-5-haiku", Decimal("0.80"), "balanced", healthy=True),
            ModelEndpoint("groq", "llama-3.1-8b-instant", Decimal("0.08"), "cheap", healthy=True),
        ]
        self.logs: List[Dict[str, Any]] = []
        
        # Define routing strategy based on complexity
        self.primary_route = {
            "simple": ["groq", "openai", "azure"],
            "moderate": ["openai", "azure", "anthropic"],
            "complex": ["openai", "azure", "anthropic"],
        }
        
        logger.info("AIGateway initialized successfully")

    def set_provider_health(self, provider: str, healthy: bool) -> None:
        logger.info(f"Setting provider {provider} health to {healthy}")
        for endpoint in self.endpoints:
            if endpoint.provider == provider:
                endpoint.healthy = healthy
        logger.info(f"Provider {provider} health updated successfully")

    def _endpoint_for_provider(self, provider: str) -> Optional[ModelEndpoint]:
        logger.debug(f"Finding endpoint for provider {provider}")
        for endpoint in self.endpoints:
            if endpoint.provider == provider:
                logger.debug(f"Found endpoint for provider {provider}")
                return endpoint
        logger.debug(f"No endpoint found for provider {provider}")
        return None

    @staticmethod
    def _estimate_tokens(receipt: Dict[str, Any]) -> int:
        logger.debug("Estimating tokens for receipt")
        base = 250
        note = str(receipt.get("note", ""))
        attendees = int(receipt.get("attendees", 1) or 1)
        tokens = base + min(len(note), 500) + attendees * 20
        logger.debug(f"Estimated tokens: {tokens}")
        return tokens

    @staticmethod
    def _estimate_cost(tokens: int, cost_per_1k_tokens: Decimal) -> Decimal:
        logger.debug("Estimating cost for tokens")
        cost = (Decimal(tokens) / Decimal(1000)) * cost_per_1k_tokens
        logger.debug(f"Estimated cost: {cost}")
        return cost

    def route_and_infer(self, receipt: Dict[str, Any]) -> GatewayResponse:
        logger.info(f"Routing and inferring for receipt: {receipt.get('id', 'unknown')}")
        complexity = self.classifier.classify(receipt)
        logger.info(f"Classified receipt complexity as: {complexity}")
        ordered_providers = self.primary_route[complexity]
        tokens = self._estimate_tokens(receipt)
        logger.debug(f"Using provider order: {ordered_providers}")
        
        for provider in ordered_providers:
            endpoint = self._endpoint_for_provider(provider)
            if not endpoint:
                continue
            if not endpoint.healthy:
                self._log(provider, endpoint.model, complexity, False, "provider_unhealthy", tokens, Decimal("0"))
                continue

            # Simulate success once healthy provider is selected.
            cost = self._estimate_cost(tokens, endpoint.cost_per_1k_tokens)
            self._log(provider, endpoint.model, complexity, True, "success", tokens, cost)
            logger.info(f"Successfully routed to {provider} using {endpoint.model} for {complexity} request")
            return GatewayResponse(
                ok=True,
                provider=provider,
                model=endpoint.model,
                reason=f"Routed via {complexity} policy",
                tokens=tokens,
                estimated_cost_usd=cost.quantize(Decimal("0.0001")),
            )

        # No healthy providers in route chain
        self._log("none", "none", complexity, False, "all_providers_failed", tokens, Decimal("0"))
        logger.error("All configured providers failed health checks")
        return GatewayResponse(
            ok=False,
            provider="none",
            model="none",
            reason="All configured providers failed health checks",
            tokens=tokens,
            estimated_cost_usd=Decimal("0"),
        )

    def _log(
        self,
        provider: str,
        model: str,
        complexity: str,
        ok: bool,
        event: str,
        tokens: int,
        cost: Decimal,
    ) -> None:
        self.logs.append(
            {
                "time": datetime.now(timezone.utc).isoformat(timespec="seconds").replace('+00:00', 'Z'),
                "provider": provider,
                "model": model,
                "complexity": complexity,
                "ok": ok,
                "event": event,
                "tokens": tokens,
                "estimated_cost_usd": str(cost.quantize(Decimal("0.0001"))),
            }
        )

    def total_cost(self) -> Decimal:
        logger.info("Calculating total cost across all gateway operations")
        total = Decimal("0")
        for row in self.logs:
            total += Decimal(row["estimated_cost_usd"])
        logger.info(f"Total cost calculated: ${total}")
        return total.quantize(Decimal("0.0001"))

    def generate_gateway_config_yaml(self) -> str:
        logger.info("Generating gateway configuration YAML")
        config = (
            "version: 1\n"
            "gateway:\n"
            "  logging: enabled\n"
            "  cost_tracking: enabled\n"
            "  timeout_seconds: 30\n"
            "providers:\n"
            "  - name: openai\n"
            "    model: gpt-4o-mini\n"
            "    role: primary\n"
            "  - name: azure\n"
            "    model: gpt-4o-mini\n"
            "    role: failover\n"
            "  - name: anthropic\n"
            "    model: claude-3-5-haiku\n"
            "    role: failover\n"
            "  - name: groq\n"
            "    model: llama-3.1-8b-instant\n"
            "    role: low_cost\n"
            "routing:\n"
            "  simple: [groq, openai, azure]\n"
            "  moderate: [openai, azure, anthropic]\n"
            "  complex: [openai, azure, anthropic]\n"
            "fallback:\n"
            "  strategy: ordered_failover\n"
            "  on_error: true\n"
        )
        logger.info("Gateway configuration YAML generated successfully")
        return config


def sample_receipts() -> Dict[str, Dict[str, Any]]:
    return {
        "SIMPLE-COFFEE": {
            "id": "SIMPLE-COFFEE",
            "category": "Coffee",
            "total": 6.50,
            "note": "Team coffee during sprint planning",
            "attendees": 1,
        },
        "MODERATE-TRAVEL": {
            "id": "MODERATE-TRAVEL",
            "category": "Travel",
            "total": 85.00,
            "note": "Airport rideshare to client office",
            "attendees": 1,
        },
        "COMPLEX-DINNER": {
            "id": "COMPLEX-DINNER",
            "category": "Client Dinner",
            "total": 420.00,
            "note": "Client dinner with exception check for VP attendees",
            "attendees": 5,
        },
    }
