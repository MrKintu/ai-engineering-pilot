from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from capstone_core2 import CapstoneEngine, sample_capstone_inputs


st.set_page_config(page_title="SnapAudit Capstone", layout="wide")


@st.cache_resource
def get_engine() -> CapstoneEngine:
    try:
        engine = CapstoneEngine()
        # Test Ollama connectivity
        if hasattr(engine, 'route_layer') and engine.route_layer:
            st.success("✅ Ollama router initialized successfully")
        if hasattr(engine, '_retrieval_mode') and 'ollama' in engine._retrieval_mode:
            st.success("✅ Ollama RAG system initialized successfully")
        return engine
    except Exception as e:
        st.error(f"❌ Failed to initialize CapstoneEngine: {e}")
        st.info("Please ensure Ollama is running and environment variables are set correctly.")
        raise


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
    
    # Show Ollama indicator for routing
    router_mode = routing.get("mode", "")
    ollama_indicator = "🤖" if "ollama" in router_mode else "🔧"
    c2.metric(f"Intent {ollama_indicator}", routing.get("intent", "N/A"))
    
    c3.metric("Decision", agentic.get("status", "N/A"))
    c4.metric("Gateway", gateway.get("provider", "N/A"))
    
    # Show module usage details
    with st.expander("🔍 Module Usage Details", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**AI Models Used:**")
            st.write(f"- Router: {routing.get('router_model', 'N/A')}")
            if "ollama" in router_mode:
                st.success("✅ Using local Ollama for routing")
            else:
                st.info("ℹ️ Using fallback routing")
        
        with col2:
            st.write("**Retrieval System:**")
            retrieval_mode = retrieval.get("mode", "")
            if "ollama" in retrieval_mode:
                st.success("✅ Using Ollama-enabled RAG")
                st.write(f"- Mode: {retrieval_mode}")
            else:
                st.info("ℹ️ Using keyword fallback")
                st.write(f"- Mode: {retrieval_mode}")

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
        st.sidebar.image(uploaded, caption="Uploaded receipt", width='content')
        extract_clicked = st.sidebar.button("Extract Text from Image", width='stretch')
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

# Check Ollama availability and show guidance
ollama_available = (
    hasattr(engine, 'route_layer') and engine.route_layer and
    hasattr(engine, '_retrieval_mode') and 'ollama' in engine._retrieval_mode
)

if not ollama_available:
    st.warning("⚠️ **Ollama Integration Not Fully Available**")
    st.info("""
    The app is running in fallback mode. For full Ollama integration:
    
    1. **Start Ollama**: `ollama serve`
    2. **Pull Models**: 
       - `ollama pull gemma3`
       - `ollama pull embeddinggemma`
    3. **Set Environment Variables** (see Ollama Integration Status below)
    4. **Restart the app**
    
    The app will work with fallbacks but routing and retrieval will be limited.
    """)
else:
    st.success("🎉 **Ollama Integration Active**")
    st.info("Local AI models are ready for routing and retrieval!")

st.title("Module 10: SnapAudit Comprehensive Capstone")
st.caption("Integrated workflow across Modules 1-9 with unified reporting")

# Add Ollama status indicator
with st.expander("🤖 Ollama Integration Status", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.success("✅ Module 1: Semantic Router (Ollama)")
        st.success("✅ Module 3: RAG Systems (Ollama)")
    with col2:
        st.info("ℹ️ Modules 5-9: Original implementations")
        st.info("ℹ️ Module 8: Security middleware")
    
    st.markdown("**Environment Variables Required:**")
    st.code("""
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=embeddinggemma:latest
OLLAMA_MODEL=gemma3:latest
    """, language="bash")
    
    # Add Ollama connection test
    if st.button("🔍 Test Ollama Connection"):
        with st.spinner("Testing Ollama connectivity..."):
            try:
                # Test routing
                if engine.route_layer:
                    test_intent = engine.module1_route("test coffee expense")
                    st.success(f"✅ Router test successful: {test_intent.get('intent', 'N/A')}")
                
                # Test retrieval
                if hasattr(engine, '_retrieval_mode') and 'ollama' in engine._retrieval_mode:
                    test_retrieval = engine.module3_retrieve("daily per diem", top_k=1)
                    st.success(f"✅ RAG test successful: {len(test_retrieval.get('results', []))} results")
                
                st.success("🎉 All Ollama components are working!")
                
            except Exception as e:
                st.error(f"❌ Ollama connection failed: {e}")
                st.info("Please check:")
                st.info("1. Ollama is running: `ollama serve`")
                st.info("2. Environment variables are set correctly")
                st.info("3. Required models are pulled: `ollama pull gemma3`")

input_text = get_input_text(engine, samples)

run_all = st.sidebar.button("Run Capstone Analysis", width='stretch', type="primary")

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
        st.markdown("**🤖 Module 1: Semantic Router (Ollama)**")
        pretty(engine.module1_route(input_text))

    with m2:
        st.markdown("**📄 Module 2: Extraction**")
        pretty(engine.module2_extract(input_text))

    with m3:
        ollama_status = "🤖" if hasattr(engine, '_retrieval_mode') and 'ollama' in engine._retrieval_mode else "🔧"
        st.markdown(f"**{ollama_status} Module 3: Retrieval (Ollama)**")
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
