from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import math
import random
import time
from typing import Any, Callable, Dict, List, Tuple


@dataclass
class QueryMetrics:
    query: str
    cached: bool
    latency_ms: float
    estimated_cost_usd: Decimal
    tokens: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "cached": self.cached,
            "latency_ms": round(self.latency_ms, 3),
            "estimated_cost_usd": str(self.estimated_cost_usd),
            "tokens": self.tokens,
        }


class SemanticCache:
    """In-memory semantic cache using simple token-overlap similarity."""

    def __init__(self, similarity_threshold: float = 0.82):
        self.similarity_threshold = similarity_threshold
        self.store: Dict[str, Dict[str, Any]] = {}
        self.log: List[Dict[str, Any]] = []

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        cleaned = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text)
        return {tok for tok in cleaned.split() if tok}

    def similarity(self, a: str, b: str) -> float:
        ta = self._tokenize(a)
        tb = self._tokenize(b)
        if not ta or not tb:
            return 0.0
        intersection = len(ta.intersection(tb))
        union = len(ta.union(tb))
        return intersection / union

    def get(self, query: str) -> Tuple[bool, Dict[str, Any] | None, str | None, float]:
        best_key = None
        best_score = -1.0

        for key in self.store:
            score = self.similarity(query, key)
            if score > best_score:
                best_score = score
                best_key = key

        hit = best_key is not None and best_score >= self.similarity_threshold
        value = self.store.get(best_key) if hit else None
        self._log("cache_get", query, hit, best_score)
        return hit, value, best_key if hit else None, best_score

    def put(self, query: str, answer_payload: Dict[str, Any]) -> None:
        self.store[query] = answer_payload
        self._log("cache_put", query, True, 1.0)

    def _log(self, action: str, query: str, hit: bool, score: float) -> None:
        self.log.append(
            {
                "time": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "action": action,
                "query": query,
                "hit": hit,
                "score": round(score, 4),
                "cache_size": len(self.store),
            }
        )


class LLMServiceSimulator:
    """Simulates LLM latency/cost for performance experiments."""

    COST_PER_1K_TOKENS = Decimal("0.10")

    def answer(self, query: str, system_prompt_tokens: int = 180) -> Dict[str, Any]:
        user_tokens = max(8, len(query) // 4)
        output_tokens = 40
        total_tokens = system_prompt_tokens + user_tokens + output_tokens

        # Simulated latency: base + token-dependent.
        latency_ms = 120 + total_tokens * 0.35
        time.sleep(latency_ms / 1000.0)

        cost = (Decimal(total_tokens) / Decimal(1000)) * self.COST_PER_1K_TOKENS

        answer = self._rule_answer(query)
        return {
            "answer": answer,
            "tokens": total_tokens,
            "latency_ms": latency_ms,
            "estimated_cost_usd": cost.quantize(Decimal("0.0001")),
        }

    @staticmethod
    def _rule_answer(query: str) -> str:
        q = query.lower()
        if "per diem" in q:
            return "The standard daily per diem is $75 for domestic travel."
        if "meal limit" in q:
            return "Individual meal limit is $25 unless executive exceptions apply."
        return "Please refer to the expense policy section relevant to your category."


def caching_decorator(
    cache: SemanticCache,
    service: LLMServiceSimulator,
) -> Callable[[str, int], Tuple[str, QueryMetrics]]:
    def wrapped(query: str, system_prompt_tokens: int = 180) -> Tuple[str, QueryMetrics]:
        start = time.perf_counter()
        hit, payload, _, _ = cache.get(query)

        if hit and payload:
            latency = (time.perf_counter() - start) * 1000
            metrics = QueryMetrics(
                query=query,
                cached=True,
                latency_ms=latency,
                estimated_cost_usd=Decimal("0"),
                tokens=0,
            )
            return payload["answer"], metrics

        resp = service.answer(query, system_prompt_tokens=system_prompt_tokens)
        cache.put(query, resp)
        latency = (time.perf_counter() - start) * 1000
        metrics = QueryMetrics(
            query=query,
            cached=False,
            latency_ms=latency,
            estimated_cost_usd=resp["estimated_cost_usd"],
            tokens=resp["tokens"],
        )
        return resp["answer"], metrics

    return wrapped


def batch_infer(queries: List[str], batch_size: int = 10) -> Dict[str, Any]:
    """Simulate batch processing speedup vs one-by-one calls."""
    service = LLMServiceSimulator()

    # Non-batched baseline
    start_single = time.perf_counter()
    for q in queries:
        _ = service.answer(q)
    single_ms = (time.perf_counter() - start_single) * 1000

    # Batched simulation: amortized overhead
    start_batch = time.perf_counter()
    for i in range(0, len(queries), batch_size):
        chunk = queries[i : i + batch_size]
        # Simulated batch latency model
        avg_tokens = 230
        batch_latency_ms = 90 + len(chunk) * avg_tokens * 0.18
        time.sleep(batch_latency_ms / 1000.0)
    batch_ms = (time.perf_counter() - start_batch) * 1000

    speedup = single_ms / batch_ms if batch_ms > 0 else math.inf
    return {
        "queries": len(queries),
        "batch_size": batch_size,
        "single_ms": round(single_ms, 2),
        "batch_ms": round(batch_ms, 2),
        "speedup_x": round(speedup, 2),
    }


def generate_query_load(n: int = 200, seed: int = 42) -> List[str]:
    rnd = random.Random(seed)
    base = [
        "What is the daily per diem?",
        "What is the meal limit?",
        "Can VP approve first class?",
        "How many attendees allowed for client dinner?",
        "Is coffee reimbursable?",
    ]

    queries = []
    for _ in range(n):
        q = rnd.choice(base)
        if rnd.random() < 0.5:
            q = q.replace("?", "")
        if rnd.random() < 0.3:
            q = q + " please"
        queries.append(q)
    return queries


def profile_prompt_optimization(query: str) -> Dict[str, Any]:
    service = LLMServiceSimulator()

    # Long prompt scenario
    long_resp = service.answer(query, system_prompt_tokens=260)
    # Short prompt scenario
    short_resp = service.answer(query, system_prompt_tokens=100)

    token_reduction = long_resp["tokens"] - short_resp["tokens"]
    cost_reduction = Decimal(long_resp["estimated_cost_usd"]) - Decimal(short_resp["estimated_cost_usd"])

    return {
        "long_prompt_tokens": long_resp["tokens"],
        "short_prompt_tokens": short_resp["tokens"],
        "token_reduction": token_reduction,
        "long_prompt_cost": str(long_resp["estimated_cost_usd"]),
        "short_prompt_cost": str(short_resp["estimated_cost_usd"]),
        "cost_reduction": str(cost_reduction.quantize(Decimal("0.0001"))),
    }
