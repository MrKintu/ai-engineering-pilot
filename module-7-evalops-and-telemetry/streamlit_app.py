from __future__ import annotations

import json
from pathlib import Path
import sys

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from evalops_core import make_golden_dataset, SnapAuditPolicyModel, TelemetryCollector, evaluate_model


@st.cache_data(show_spinner=False)
def load_dataset(size: int, seed: int):
    return make_golden_dataset(size=size, seed=seed)


def main() -> None:
    st.set_page_config(page_title="Module 7 EvalOps & Telemetry", layout="wide")
    st.title("Module 7: EvalOps and AI Telemetry")
    st.caption("Golden dataset evaluation + CI gate + telemetry debugging")

    with st.sidebar:
        st.header("Eval Config")
        variant = st.selectbox("Model Variant", ["baseline", "friendly_regression"], index=0)
        threshold = st.number_input("Accuracy Threshold", min_value=0.0, max_value=1.0, value=0.99, step=0.01)
        dataset_size = st.number_input("Golden Dataset Size", min_value=20, max_value=500, value=100, step=10)
        dataset_seed = st.number_input("Random Seed", min_value=0, max_value=9999, value=42, step=1)

    dataset = load_dataset(size=int(dataset_size), seed=int(dataset_seed))

    if st.button("Run Evaluation", type="primary"):
        model = SnapAuditPolicyModel(variant=variant)
        telemetry = TelemetryCollector()
        metrics = evaluate_model(dataset, model, telemetry)

        st.session_state["metrics"] = metrics
        st.session_state["telemetry"] = telemetry.events
        st.session_state["variant"] = variant
        st.session_state["threshold"] = float(threshold)

    metrics = st.session_state.get("metrics")
    telemetry = st.session_state.get("telemetry")

    if not metrics:
        st.info("Run evaluation to see metrics and traces.")
        return

    gate_pass = metrics["accuracy"] >= st.session_state["threshold"]

    st.subheader("Evaluation Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy", f"{metrics['accuracy']:.4f}")
    c2.metric("Faithfulness", f"{metrics['faithfulness']:.4f}")
    c3.metric("Answer Relevance", f"{metrics['answer_relevance']:.4f}")
    c4.metric("Failures", str(len(metrics["failures"])))

    if gate_pass:
        st.success(f"CI Gate PASSED: accuracy {metrics['accuracy']:.4f} >= {st.session_state['threshold']:.4f}")
    else:
        st.error(f"CI Gate BLOCKED: accuracy {metrics['accuracy']:.4f} < {st.session_state['threshold']:.4f}")

    st.subheader("Failure Analysis")
    failures = metrics.get("failures", [])
    if not failures:
        st.info("No failures in this run.")
    else:
        idx = st.slider("Failure Index", min_value=0, max_value=len(failures) - 1, value=0)
        st.json(failures[idx])

    st.subheader("Telemetry Events")
    st.dataframe(telemetry, use_container_width=True)

    st.subheader("Export Artifacts")
    result_json = json.dumps(metrics, indent=2)
    telem_json = json.dumps(telemetry, indent=2)

    st.download_button("Download eval_results.json", data=result_json, file_name="eval_results.json", mime="application/json")
    st.download_button("Download telemetry_log.json", data=telem_json, file_name="telemetry_log.json", mime="application/json")

    if st.button("Write artifacts to module folder"):
        out_dir = Path(__file__).resolve().parent
        (out_dir / "eval_results.json").write_text(result_json)
        (out_dir / "telemetry_log.json").write_text(telem_json)
        st.success("Artifacts written to module-7-evalops-and-telemetry/")


if __name__ == "__main__":
    main()
