# Module 6: AI Gateways & MLOps for LLM Deployment

## The SnapAudit Challenge

Every engineer is using their own key, costs are opaque, and outages can break the pipeline.
We need a centralized gateway for routing, failover, and cost visibility.

## Learning Objectives

1. Deploy an AI Gateway pattern to centralize all LLM traffic.
2. Configure smart routing:
   - simple receipts -> low-cost models
   - complex receipts -> higher-capability models
3. Implement provider fallback:
   - reroute automatically when primary providers are unhealthy.

## Build Artifacts

- `ai_gateway_core.py` - routing logic, failover, logs, cost tracking, config generation
- `module-6-ai-gateways.ipynb` - step-by-step implementation and smoke checks
- `streamlit_app.py` - interactive gateway simulation UI
- `gateway_config.yaml` - production-style routing/failover config artifact

## Run

1. Open notebook:
   - `module-6-ai-gateways/module-6-ai-gateways.ipynb`

2. Run Streamlit app:
   ```bash
   uv run streamlit run module-6-ai-gateways/streamlit_app.py
   ```
