# Module 9: Performance & Cost Engineering for AI Systems

## The SnapAudit Challenge

We are burning cash and adding latency on repetitive policy queries.  
Example: thousands of users ask the same per-diem question every morning.

## Learning Objectives

1. Implement semantic caching to cut repeated-query latency and cost.
2. Improve throughput using batching concepts.
3. Profile token/cost impact of prompt design.

## Build Artifacts

- `perf_cost_core.py` - semantic cache, simulator, batching/profile utilities
- `perf_benchmark.py` - benchmark script with pass/fail performance gate
- `module-9-performance-and-cost-engineering.ipynb` - stepwise optimization notebook
- `streamlit_app.py` - interactive performance and cost dashboard

## Run

1. Benchmark script:
   ```bash
   cd module-9-performance-and-cost-engineering
   python3 perf_benchmark.py
   ```

2. Streamlit app:
   ```bash
   uv run streamlit run module-9-performance-and-cost-engineering/streamlit_app.py
   ```
