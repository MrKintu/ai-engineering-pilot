from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from capstone_core import CapstoneEngine, sample_capstone_inputs


st.set_page_config(page_title="SnapAudit Capstone", layout="wide")


@st.cache_resource
def get_engine() -> CapstoneEngine:
    return CapstoneEngine()


def pretty(obj):
    st.code(json.dumps(obj, indent=2), language="json")


def decision_color(status: str) -> str:
    if status in {"approved", "success"}:
        return "green"
    if status in {"blocked_by_security", "flagged_for_human", "denied", "error"}:
        return "red"
    return "orange"


def run_pipeline(engine: CapstoneEngine, text: str) -> dict:
    return engine.run_capstone(text).to_dict()


def render_report(result: dict):
    security = result["security"]
    routing = result["routing"]
    extraction = result["extraction"]
    agentic = result["agentic"]
    retrieval = result.get("retrieval", {})
    gateway = result.get("gateway", {})
    perf = result.get("perf", {})

    st.subheader("Executive Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Security", "Allowed" if security.get("allowed") else "Blocked")
    c2.metric("Intent", routing.get("intent", "N/A"))
    c3.metric("Decision", agentic.get("status", "N/A"))
    c4.metric("Gateway", gateway.get("provider", "N/A"))

    status = agentic.get("status", "unknown")
    st.markdown(f"**Outcome:** :{decision_color(status)}[{status}]  ")
    if agentic.get("reason"):
        st.write(f"Reason: {agentic['reason']}")

    st.subheader("Extracted Receipt Data")
    c5, c6, c7 = st.columns(3)
    c5.metric("Merchant", extraction.get("merchant", "Unknown"))
    c6.metric("Date", extraction.get("date", "Unknown"))
    c7.metric("Total", f"${(extraction.get('total') or 0):.2f}")

    st.subheader("Policy Evidence")
    results = retrieval.get("results", [])
    if results:
        best = results[0]
        st.write(f"Top match: **{best.get('title', 'N/A')}** (Section {best.get('section', 'N/A')})")
        st.caption(best.get("preview", ""))
        with st.expander("Top retrieval matches"):
            for row in results:
                st.write(
                    f"- Section {row.get('section')} | {row.get('title')} | score={row.get('score', 0):.2f}"
                )
                st.caption(row.get("preview", ""))
    else:
        st.info("No retrieval evidence available.")

    st.subheader("Ops Snapshot")
    c8, c9, c10 = st.columns(3)
    c8.metric("Gateway Tokens", gateway.get("tokens", 0))
    c9.metric("Gateway Cost", f"${gateway.get('estimated_cost_usd', '0')}")
    perf_metrics = perf.get("metrics", {})
    c10.metric("Perf Cached", str(perf_metrics.get("cached", False)))

    with st.expander("Technical Details (full JSON)"):
        pretty(result)


def get_input_text(engine: CapstoneEngine, samples: dict) -> str:
    mode = st.sidebar.radio("Input Mode", ["Text", "Image"], horizontal=True)

    if mode == "Text":
        sample_name = st.sidebar.selectbox("Sample", options=["simple", "complex", "injection"])
        return st.sidebar.text_area(
            "Expense note / receipt text",
            value=samples[sample_name],
            height=220,
        )

    uploaded = st.sidebar.file_uploader("Upload receipt image", type=["png", "jpg", "jpeg"])
    if uploaded:
        st.sidebar.image(uploaded, caption="Uploaded receipt", use_container_width=True)
        extract_clicked = st.sidebar.button("Extract Text from Image", use_container_width=True)
        if extract_clicked:
            response = engine.extract_text_from_image(uploaded.getvalue(), mime_type=uploaded.type or "image/png")
            if response.get("ok"):
                st.session_state["image_text"] = response["text"]
                st.sidebar.success(f"Text extracted via {response.get('model', 'vision model')}")
            else:
                st.sidebar.error(response.get("error", "Image text extraction failed."))

    image_text = st.sidebar.text_area(
        "Extracted/Editable text",
        value=st.session_state.get("image_text", ""),
        height=220,
        placeholder="Upload an image and click 'Extract Text from Image'.",
    )
    return image_text


engine = get_engine()
samples = sample_capstone_inputs()

st.title("Module 10: SnapAudit Comprehensive Capstone")
st.caption("Integrated workflow across Modules 1-9 with unified reporting")

input_text = get_input_text(engine, samples)

run_all = st.sidebar.button("Run Capstone Analysis", use_container_width=True, type="primary")

report_tab, workbench_tab = st.tabs(["Capstone Report", "Module Workbench"])

with report_tab:
    st.write("Run analysis to generate a concise compliance report.")
    if run_all:
        if not input_text.strip():
            st.error("Provide receipt text (or extract from image) before running analysis.")
        else:
            result = run_pipeline(engine, input_text)
            render_report(result)

with workbench_tab:
    st.write("Inspect each module independently using the same input.")

    m1, m2, m3, m4, m5, m6, m7, m8, m9 = st.tabs(
        [
            "M1 Router",
            "M2 Extractor",
            "M3 Retrieval",
            "M4 Agentic",
            "M5 MCP",
            "M6 Gateway",
            "M7 EvalOps",
            "M8 Security",
            "M9 Perf/Cost",
        ]
    )

    with m8:
        pretty(engine.module8_scan(input_text))

    with m1:
        pretty(engine.module1_route(input_text))

    with m2:
        pretty(engine.module2_extract(input_text))

    with m3:
        query = st.text_input("Retrieval query", value="daily per diem")
        top_k = st.slider("Top K", min_value=1, max_value=5, value=3)
        if st.button("Run Retrieval"):
            pretty(engine.module3_retrieve(query, top_k=top_k))

    with m4:
        extracted = engine.module2_extract(input_text)
        pretty({"extracted": extracted, "decision": engine.module4_agentic_decision(extracted)})

    with m5:
        tx_id = st.selectbox("Transaction ID", ["T1001", "T1002", "T1003", "T1004"])
        role = st.selectbox("Actor role", ["agent", "manager", "finance_admin", "employee"])
        policy_approved = st.checkbox("Policy approved", value=True)
        digital_key = st.text_input("Digital key (for >$10k finance admin approvals)", value="")
        if st.button("Run MCP Action"):
            key = digital_key if digital_key.strip() else None
            pretty(engine.module5_mcp_action(tx_id, policy_approved=policy_approved, role=role, digital_key=key))

    with m6:
        route = engine.module1_route(input_text)
        extracted = engine.module2_extract(input_text)
        payload = {
            "id": "CAPSTONE-DEMO",
            "category": "Client Dinner" if route["intent"] == "complex_client_dinner" else "Coffee",
            "total": extracted.get("total") or 0,
            "note": input_text,
            "attendees": 5 if route["intent"] == "complex_client_dinner" else 1,
        }
        pretty(engine.module6_gateway_route(payload))

    with m7:
        variant = st.selectbox("Model variant", ["baseline", "friendly_regression"])
        size = st.slider("Dataset size", min_value=20, max_value=200, value=50, step=10)
        if st.button("Run Eval"):
            pretty(engine.module7_eval(variant=variant, size=size))

    with m9:
        q = st.text_input("Perf query", value="What is the daily per diem?")
        if st.button("Run Perf Query"):
            first = engine.module9_perf_once(q)
            second = engine.module9_perf_once(q)
            pretty({"first_call": first, "second_call": second})

st.divider()
st.caption(f"App path: {Path(__file__).resolve()}")
