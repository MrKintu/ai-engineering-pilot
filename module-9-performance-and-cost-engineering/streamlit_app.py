from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import sys

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from perf_cost_core import (
    SemanticCache,
    LLMServiceSimulator,
    caching_decorator,
    batch_infer,
    generate_query_load,
    profile_prompt_optimization,
)


@st.cache_resource(show_spinner=False)
def init_runtime(threshold: float):
    service = LLMServiceSimulator()
    cache = SemanticCache(similarity_threshold=threshold)
    call = caching_decorator(cache, service)
    return service, cache, call


def _render_sidebar() -> tuple[float, bool]:
    """Render sidebar configuration controls."""
    with st.sidebar:
        st.header("Config")
        threshold = st.slider("Semantic Similarity Threshold", min_value=0.5, max_value=0.95, value=0.82, step=0.01)
        reset_cache = st.button("Reset Cache")
    
    return threshold, reset_cache

def _initialize_runtime(threshold: float, reset_cache: bool) -> tuple:
    """Initialize runtime components."""
    if reset_cache:
        st.session_state.pop("runtime", None)
        st.session_state.pop("metrics_log", None)
    
    if "runtime" not in st.session_state:
        st.session_state["runtime"] = init_runtime(threshold)
    
    return st.session_state["runtime"]

def _render_single_query_section(_cached_call):
    """Render single query testing section."""
    st.subheader("Single Query")
    query = st.text_input("Query", value="What is the daily per diem?")
    
    if st.button("Run Query", type="primary"):
        answer, metrics = _cached_call(query)
        row = metrics.to_dict()
        row["answer"] = answer
        st.session_state["metrics_log"].append(row)
    
    if st.session_state["metrics_log"]:
        latest = st.session_state["metrics_log"][-1]
        if latest["cached"]:
            st.success("Cache hit: returned instantly with $0 incremental cost")
        else:
            st.info("Cache miss: model call executed")
        st.json(latest)

def _render_load_simulation_section(_cached_call):
    """Render load simulation section."""
    st.subheader("Load Simulation")
    c1, c2 = st.columns(2)
    with c1:
        load_n = st.number_input("Number of queries", min_value=20, max_value=1000, value=200, step=20)
    with c2:
        seed = st.number_input("Seed", min_value=0, max_value=9999, value=42, step=1)
    
    if st.button("Run Load Test"):
        queries = generate_query_load(n=int(load_n), seed=int(seed))
        hits = 0
        misses = 0
        cost = Decimal("0")
        latencies = []
        
        for q in queries:
            _, m = _cached_call(q)
            if m.cached:
                hits += 1
            else:
                misses += 1
            cost += m.estimated_cost_usd
            latencies.append(m.latency_ms)
        
        st.session_state["load_stats"] = {
            "queries": len(queries),
            "hits": hits,
            "misses": misses,
            "cache_hit_rate": round(hits / len(queries), 4),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
            "total_estimated_cost_usd": str(cost.quantize(Decimal("0.0001"))),
        }
    
    if "load_stats" in st.session_state:
        st.json(st.session_state["load_stats"])

def _render_benchmark_sections(_cached_call):
    """Render batch and prompt optimization benchmark sections."""
    if st.button("Run Batch Benchmark"):
        q = generate_query_load(n=60, seed=7)
        st.session_state["batch_stats"] = batch_infer(q, batch_size=10)
    
    if st.button("Run Prompt Optimization Profile"):
        st.session_state["prompt_stats"] = profile_prompt_optimization("What is the daily per diem?")
    
    colb, colp = st.columns(2)
    with colb:
        if "batch_stats" in st.session_state:
            st.markdown("**Batch Benchmark**")
            st.json(st.session_state["batch_stats"])
    with colp:
        if "prompt_stats" in st.session_state:
            st.markdown("**Prompt Optimization**")
            st.json(st.session_state["prompt_stats"])

def _render_telemetry_and_export(cache):
    """Render cache telemetry and export options."""
    st.subheader("Cache Telemetry")
    st.dataframe(cache.log, use_container_width=True)
    
    st.subheader("Export Report")
    report = {
        "latest_query": st.session_state["metrics_log"][-1] if st.session_state["metrics_log"] else None,
        "load_stats": st.session_state.get("load_stats"),
        "batch_stats": st.session_state.get("batch_stats"),
        "prompt_stats": st.session_state.get("prompt_stats"),
    }
    report_json = json.dumps(report, indent=2)
    st.download_button("Download perf_report.json", data=report_json, file_name="perf_report.json", mime="application/json")
    
    if st.button("Write perf_report.json to module folder"):
        out = Path(__file__).resolve().parent / "perf_report.json"
        out.write_text(report_json)
        st.success(f"Wrote {out}")

def main() -> None:
    """Entry point for Streamlit app, configures and runs performance testing UI."""
    st.set_page_config(page_title="Module 9 Performance & Cost", layout="wide")
    st.title("Module 9: Performance and Cost Engineering")
    st.caption("Semantic caching + batching + prompt optimization for AI workload efficiency")

    # Initialize metrics log
    if "metrics_log" not in st.session_state:
        st.session_state["metrics_log"] = []

    # Render sidebar and get configuration
    threshold, reset_cache = _render_sidebar()
    
    # Initialize runtime
    _, cache, cached_call = _initialize_runtime(threshold, reset_cache)
    
    # Render all UI sections
    _render_single_query_section(cached_call)
    _render_load_simulation_section(cached_call)
    _render_benchmark_sections(cached_call)
    _render_telemetry_and_export(cache)


if __name__ == "__main__":
    main()
