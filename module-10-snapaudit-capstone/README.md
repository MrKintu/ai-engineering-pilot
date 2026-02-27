# Module 10: SnapAudit Capstone

This capstone integrates features from modules 1-9 into a single application:

- Module 1: Semantic routing
- Module 2: Structured extraction
- Module 3: Retrieval (BM25/fallback)
- Module 4: Agentic workflow decisions
- Module 5: MCP-secured ERP actions
- Module 6: AI gateway routing/failover
- Module 7: EvalOps + telemetry
- Module 8: Governance + safety shield
- Module 9: Performance and cost engineering

## Files

- `capstone_core.py`: unified integration engine
- `module-10-snapaudit-capstone.ipynb`: notebook walkthrough
- `streamlit_app.py`: interactive UI
- `test_capstone.py`: end-to-end and module-level tests

## Run Notebook

Open `module-10-snapaudit-capstone.ipynb` and execute cells sequentially.

## Run Streamlit

From repository root:

```bash
streamlit run module-10-snapaudit-capstone/streamlit_app.py
```

## Run Tests

From repository root:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 module-10-snapaudit-capstone/test_capstone.py
```
