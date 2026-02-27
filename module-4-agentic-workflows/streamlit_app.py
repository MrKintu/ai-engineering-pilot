from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
ROOT_ENV_PATH = REPO_ROOT / ".env"
INTEGRATED_DIR = REPO_ROOT / "snapaudit-integrated"

if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


def load_root_env_file() -> None:
    if not ROOT_ENV_PATH.exists():
        return

    for line in ROOT_ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class PolicyVerdictLike:
    approved: bool
    reason: str
    citations: List[str]


class MockPolicyRetriever:
    def check_compliance(self, receipt_data: Dict[str, Any], role: str = "Employee") -> PolicyVerdictLike:
        total = float(receipt_data.get("total", 0))
        category = str(receipt_data.get("category", "")).lower()

        if "lunch" in category or "meal" in category:
            limit = 50 if role == "Vice President" else 25
            approved = total <= limit
            reason = f"Within {role} meal limit (${limit})" if approved else f"Exceeds {role} meal limit (${limit})"
            return PolicyVerdictLike(approved=approved, reason=reason, citations=["Mock Section 2.1.1"])

        approved = total < 1000
        reason = "Below generic mock threshold" if approved else "Above generic mock threshold"
        return PolicyVerdictLike(approved=approved, reason=reason, citations=["Mock policy rule"])


@st.cache_resource(show_spinner=False)
def init_policy_retriever():
    sys.path.append(str(INTEGRATED_DIR))
    try:
        from policy_retriever import PolicyRetriever
    except Exception:
        return MockPolicyRetriever(), "mock (import failed)"

    pdf_path = INTEGRATED_DIR / "sample_expense_policy.pdf"
    if not pdf_path.exists():
        return MockPolicyRetriever(), "mock (missing policy PDF)"

    try:
        retriever = PolicyRetriever(str(pdf_path))
        return retriever, "real"
    except Exception as exc:
        return MockPolicyRetriever(), f"mock (PolicyRetriever init failed: {exc})"


MOCK_RECEIPTS = {
    "R001": {"id": "R001", "total": 20.00, "category": "Lunch", "merchant": "Sandwich Shop", "date": "2024-01-15"},
    "R002": {"id": "R002", "total": 200.00, "category": "Client Dinner", "merchant": "Fancy Steakhouse", "date": "2024-01-16"},
    "R003": {"id": "R003", "total": 5000.00, "category": "Office Supplies", "merchant": "Apple Store", "date": "2024-01-17"},
}


def add_trace(trace: List[Dict[str, str]], node: str, action: str, details: str) -> None:
    trace.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "node": node,
            "action": action,
            "details": details,
        }
    )


def get_receipt_tool(receipt_id: str) -> Dict[str, Any]:
    return MOCK_RECEIPTS.get(receipt_id, {})


def send_email_tool(to_email: str, subject: str, body: str) -> str:
    return f"Email sent to {to_email} with subject '{subject}'"


def check_policy_tool(policy_retriever, receipt_data: Dict[str, Any], role: str) -> Dict[str, Any]:
    verdict = policy_retriever.check_compliance(receipt_data, role)
    return {
        "approved": bool(verdict.approved),
        "reason": str(verdict.reason),
        "citations": list(verdict.citations),
    }


def run_audit_workflow(
    policy_retriever,
    role: str,
    review_threshold: float,
    receipt_id: Optional[str] = None,
    manual_receipt: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "receipt_id": receipt_id or "",
        "receipt_data": manual_receipt or {},
        "verdict": None,
        "status": "pending",
        "next_step": "",
        "messages": [],
        "trace": [],
    }

    # Planner
    add_trace(state["trace"], "planner", "start", "Planning next step")
    if not state["receipt_data"]:
        add_trace(state["trace"], "planner", "fetch_receipt", f"Fetching receipt ID {state['receipt_id']}")
        receipt = get_receipt_tool(state["receipt_id"])
        if not receipt:
            state["status"] = "error"
            add_trace(state["trace"], "planner", "error", "Receipt not found")
            return state
        state["receipt_data"] = receipt

    state["next_step"] = "check_policy"
    add_trace(state["trace"], "planner", "route", "Routing to executor for policy check")

    # Executor
    receipt = state["receipt_data"]
    add_trace(
        state["trace"],
        "executor",
        "check_policy",
        f"Category={receipt.get('category')} Total=${receipt.get('total')}",
    )
    state["verdict"] = check_policy_tool(policy_retriever, receipt, role)

    # Critic
    verdict = state["verdict"]
    total = float(receipt.get("total", 0))

    add_trace(state["trace"], "critic", "evaluate", f"Approved={verdict['approved']} total={total}")

    if verdict["approved"]:
        if total > review_threshold:
            state["status"] = "flagged_for_human"
            email_msg = send_email_tool(
                to_email="manager@company.com",
                subject=f"Manual Review Needed: {receipt.get('id', 'manual')}",
                body="High value approved receipt needs human review.",
            )
            add_trace(state["trace"], "critic", "flagged_for_human", "High value approved receipt")
            add_trace(state["trace"], "tool_send_email", "notify", email_msg)
            return state

        state["status"] = "approved"
        add_trace(state["trace"], "critic", "approved", "Auto-approved by agent")
        return state

    state["status"] = "denied"
    add_trace(state["trace"], "critic", "denied", verdict["reason"])
    return state


def render_receipt_editor() -> Dict[str, Any]:
    col1, col2 = st.columns(2)
    with col1:
        receipt_id = st.text_input("Receipt ID", value="MANUAL-001")
        total = st.number_input("Total", min_value=0.0, value=120.0, step=1.0)
        category = st.text_input("Category", value="Client Dinner")
    with col2:
        merchant = st.text_input("Merchant", value="Custom Merchant")
        date = st.text_input("Date", value="2026-02-25")

    return {
        "id": receipt_id,
        "total": float(total),
        "category": category,
        "merchant": merchant,
        "date": date,
    }


def main() -> None:
    load_root_env_file()

    st.set_page_config(page_title="Module 4 Agentic Workflows", layout="wide")
    st.title("Module 4: Agentic Workflow UI")
    st.caption("Planner -> Executor -> Critic with trace and human-in-the-loop controls")

    policy_retriever, retriever_mode = init_policy_retriever()

    with st.sidebar:
        st.header("Run Config")
        role = st.selectbox("Employee Role", ["Employee", "Manager", "Vice President"], index=0)
        review_threshold = st.number_input("Human Review Threshold", min_value=100.0, value=1000.0, step=100.0)
        st.session_state["review_threshold"] = float(review_threshold)
        st.markdown("### Policy Backend")
        st.write(f"Mode: `{retriever_mode}`")
        st.write("OPENAI key loaded" if os.getenv("OPENAI_API_KEY") else "OPENAI key missing")

    mode = st.radio("Receipt Input", ["Predefined", "Manual"], horizontal=True)

    if mode == "Predefined":
        receipt_id = st.selectbox("Select Receipt ID", list(MOCK_RECEIPTS.keys()), index=0)
        manual_receipt = None
        st.json(MOCK_RECEIPTS[receipt_id])
    else:
        receipt_id = None
        manual_receipt = render_receipt_editor()
        st.json(manual_receipt)

    col_run, col_reset = st.columns([1, 1])
    with col_run:
        if st.button("Run Audit", type="primary"):
            result = run_audit_workflow(
                policy_retriever=policy_retriever,
                role=role,
                review_threshold=st.session_state["review_threshold"],
                receipt_id=receipt_id,
                manual_receipt=manual_receipt,
            )

            st.session_state["audit_result"] = result
            st.session_state["hitl_note"] = ""

    with col_reset:
        if st.button("Clear Run"):
            st.session_state.pop("audit_result", None)
            st.session_state.pop("hitl_note", None)

    result = st.session_state.get("audit_result")
    if not result:
        st.info("Run an audit to see status, trace, and HITL actions.")
        return

    st.subheader("Audit Outcome")
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", result.get("status", "unknown"))
    c2.metric("Receipt", result.get("receipt_data", {}).get("id", "N/A"))
    c3.metric("Total", f"${float(result.get('receipt_data', {}).get('total', 0)):.2f}")

    st.markdown("**Verdict**")
    st.json(result.get("verdict", {}))

    st.subheader("Step Trace")
    st.dataframe(result.get("trace", []), use_container_width=True)

    if result.get("status") == "flagged_for_human":
        st.subheader("Human In The Loop")
        st.warning("This audit is paused for manual decision.")
        note = st.text_area("Reviewer note", value=st.session_state.get("hitl_note", ""))
        st.session_state["hitl_note"] = note

        a1, a2 = st.columns(2)
        with a1:
            if st.button("Approve Manually"):
                result["status"] = "approved_by_human"
                add_trace(result["trace"], "human", "approve", note or "Approved manually")
                st.session_state["audit_result"] = result
                st.rerun()
        with a2:
            if st.button("Deny Manually"):
                result["status"] = "denied_by_human"
                add_trace(result["trace"], "human", "deny", note or "Denied manually")
                st.session_state["audit_result"] = result
                st.rerun()


if __name__ == "__main__":
    main()
