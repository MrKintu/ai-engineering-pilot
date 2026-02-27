from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import sys

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from ai_gateway_core import AIGateway, sample_receipts


@st.cache_resource(show_spinner=False)
def init_gateway() -> AIGateway:
    return AIGateway()


def reset_gateway() -> AIGateway:
    g = AIGateway()
    st.session_state["gateway"] = g
    return g


def main() -> None:
    st.set_page_config(page_title="Module 6 AI Gateway", layout="wide")
    st.title("Module 6: AI Gateway Routing + Failover")
    st.caption("Centralized routing, fallback, logging, and cost visibility for SnapAudit")

    if "gateway" not in st.session_state:
        st.session_state["gateway"] = init_gateway()
    gateway: AIGateway = st.session_state["gateway"]

    receipts = sample_receipts()

    with st.sidebar:
        st.header("Provider Health")

        # Controls mirror real gateway health checks
        openai_ok = st.toggle("OpenAI healthy", value=next(e.healthy for e in gateway.endpoints if e.provider == "openai"))
        azure_ok = st.toggle("Azure healthy", value=next(e.healthy for e in gateway.endpoints if e.provider == "azure"))
        anthropic_ok = st.toggle("Anthropic healthy", value=next(e.healthy for e in gateway.endpoints if e.provider == "anthropic"))
        groq_ok = st.toggle("Groq healthy", value=next(e.healthy for e in gateway.endpoints if e.provider == "groq"))

        gateway.set_provider_health("openai", openai_ok)
        gateway.set_provider_health("azure", azure_ok)
        gateway.set_provider_health("anthropic", anthropic_ok)
        gateway.set_provider_health("groq", groq_ok)

        if st.button("Reset Gateway State"):
            gateway = reset_gateway()
            st.success("Gateway state reset")

    source_mode = st.radio("Receipt Source", ["Sample", "Manual"], horizontal=True)

    if source_mode == "Sample":
        rid = st.selectbox("Sample Receipt", list(receipts.keys()))
        payload: Dict[str, Any] = receipts[rid]
    else:
        c1, c2 = st.columns(2)
        with c1:
            rid = st.text_input("Receipt ID", value="MANUAL-001")
            category = st.text_input("Category", value="Client Dinner")
            total = st.number_input("Total", min_value=0.0, value=220.0, step=1.0)
        with c2:
            note = st.text_area("Note", value="Dinner with client stakeholders and VP attendee")
            attendees = st.number_input("Attendees", min_value=1, value=4, step=1)

        payload = {
            "id": rid,
            "category": category,
            "total": float(total),
            "note": note,
            "attendees": int(attendees),
        }

    st.subheader("Input Receipt")
    st.json(payload)

    if st.button("Run Through Gateway", type="primary"):
        result = gateway.route_and_infer(payload)
        st.session_state["last_result"] = result.to_dict()

    st.subheader("Gateway Result")
    if "last_result" not in st.session_state:
        st.info("Run a request to see routing output.")
    else:
        result = st.session_state["last_result"]
        if result["ok"]:
            st.success(f"Routed to {result['provider']}:{result['model']}")
        else:
            st.error(result["reason"])
        st.json(result)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Traffic Logs")
        if gateway.logs:
            st.dataframe(gateway.logs, use_container_width=True)
        else:
            st.info("No logs yet")

    with c2:
        st.subheader("Cost Summary")
        st.metric("Total Estimated Cost (USD)", str(gateway.total_cost()))
        st.markdown("**Current Providers**")
        st.dataframe([e.to_dict() for e in gateway.endpoints], use_container_width=True)

    st.subheader("gateway_config.yaml")
    config_yaml = gateway.generate_gateway_config_yaml()
    st.code(config_yaml, language="yaml")

    if st.button("Write gateway_config.yaml to module"):
        out_path = Path(__file__).resolve().parent / "gateway_config.yaml"
        out_path.write_text(config_yaml)
        st.success(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
