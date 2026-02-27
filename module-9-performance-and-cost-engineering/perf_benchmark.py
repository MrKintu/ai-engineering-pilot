from __future__ import annotations

import json
from decimal import Decimal

from perf_cost_core import (
    SemanticCache,
    LLMServiceSimulator,
    caching_decorator,
    batch_infer,
    generate_query_load,
    profile_prompt_optimization,
)


def main() -> int:
    queries = generate_query_load(n=200, seed=42)

    cache = SemanticCache(similarity_threshold=0.82)
    service = LLMServiceSimulator()
    cached_call = caching_decorator(cache, service)

    total_cost = Decimal("0")
    hits = 0
    misses = 0
    latencies = []

    for q in queries:
        _, m = cached_call(q)
        latencies.append(m.latency_ms)
        total_cost += m.estimated_cost_usd
        if m.cached:
            hits += 1
        else:
            misses += 1

    cache_hit_rate = hits / len(queries)

    batch_stats = batch_infer(queries[:60], batch_size=10)
    prompt_stats = profile_prompt_optimization("What is the daily per diem?")

    report = {
        "queries": len(queries),
        "hits": hits,
        "misses": misses,
        "cache_hit_rate": round(cache_hit_rate, 4),
        "total_estimated_cost_usd": str(total_cost.quantize(Decimal("0.0001"))),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
        "batch": batch_stats,
        "prompt_optimization": prompt_stats,
    }

    print(json.dumps(report, indent=2))

    with open("perf_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Gate: require at least 30% cache hit to count as meaningful savings.
    if cache_hit_rate < 0.30:
        print("\n❌ Performance gate failed: cache hit rate below 30%")
        return 1

    print("\n✅ Performance gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
