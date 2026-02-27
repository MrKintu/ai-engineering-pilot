# Module 7: EvalOps & AI Telemetry for Continuous Quality

## The SnapAudit Challenge

We tweaked the prompt to be friendlier, but now fraud slips through.  
How do we detect regression before deployment?

## Learning Objectives

1. Create a golden dataset of verified receipt decisions.
2. Build a CI/CD evaluation gate (accuracy, faithfulness, relevance).
3. Use telemetry traces to debug approval decisions.

## Build Artifacts

- `evalops_core.py` - dataset generation, model simulation, evaluator, telemetry collector
- `eval.py` - CI gate script (blocks if accuracy < 99%)
- `module-7-evalops-and-telemetry.ipynb` - step-by-step workshop notebook
- `streamlit_app.py` - interactive eval dashboard + telemetry explorer

## Run

1. CI-style eval run:
   ```bash
   cd module-7-evalops-and-telemetry
   python3 eval.py
   ```

2. Streamlit dashboard:
   ```bash
   uv run streamlit run module-7-evalops-and-telemetry/streamlit_app.py
   ```
