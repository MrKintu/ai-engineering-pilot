from __future__ import annotations

from decimal import Decimal
from typing import Dict, Any, Optional
import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from mcp_secure_adapter import (
    MockERPLedger,
    ERPConnectorMCPServer,
    SnapAuditAgentClient,
    RBACPolicy,
    Transaction,
)


@st.cache_resource(show_spinner=False)
def init_system() -> tuple[MockERPLedger, ERPConnectorMCPServer, SnapAuditAgentClient]:
    ledger = MockERPLedger()
    server = ERPConnectorMCPServer(ledger)
    client = SnapAuditAgentClient(server)
    return ledger, server, client


def upsert_manual_transaction(ledger: MockERPLedger, tx: Dict[str, Any]) -> str:
    tx_id = tx["transaction_id"]
    ledger.transactions[tx_id] = Transaction(
        transaction_id=tx_id,
        vendor=tx["vendor"],
        amount=Decimal(str(tx["amount"])),
        currency=tx["currency"],
        category=tx["category"],
        status="pending",
        reason="",
        updated_at="",
    )
    return tx_id


def main() -> None:
    st.set_page_config(page_title="Module 5 MCP Secure Adapter", layout="wide")
    st.title("Module 5: MCP Secure ERP Connector")
    st.caption("Safe MCP tools + RBAC guardrails for SnapAudit to interact with an ERP ledger")

    ledger, mcp_server, agent = init_system()

    with st.sidebar:
        st.header("Access Control")
        role = st.selectbox("Actor Role", ["agent", "manager", "finance_admin"], index=0)
        digital_key = st.text_input("Digital Key (for >$10k approvals)", value="", type="password")

        st.markdown("### Policy Result Input")
        policy_approved = st.toggle("Policy says APPROVE", value=True)

        st.markdown("### RBAC Rules")
        st.write("- <= $10,000: agent/manager/finance_admin can approve")
        st.write("- > $10,000: only finance_admin + correct key")

    mode = st.radio("Transaction Source", ["Existing Ledger", "Manual Entry"], horizontal=True)

    selected_tx_id: Optional[str] = None
    if mode == "Existing Ledger":
        selected_tx_id = st.selectbox("Select Transaction", sorted(ledger.transactions.keys()))
        st.json(ledger.transactions[selected_tx_id].to_dict())
    else:
        c1, c2 = st.columns(2)
        with c1:
            tx_id = st.text_input("Transaction ID", value="T2001")
            vendor = st.text_input("Vendor", value="New Vendor LLC")
            amount = st.number_input("Amount", min_value=0.0, value=15000.0, step=100.0)
        with c2:
            currency = st.text_input("Currency", value="USD")
            category = st.text_input("Category", value="Consulting")

        manual_tx = {
            "transaction_id": tx_id.strip() or "T2001",
            "vendor": vendor,
            "amount": float(amount),
            "currency": currency,
            "category": category,
        }
        st.json(manual_tx)

    run_col, reset_col = st.columns([1, 1])
    with run_col:
        if st.button("Run MCP Action", type="primary"):
            if mode == "Manual Entry":
                selected_tx_id = upsert_manual_transaction(ledger, manual_tx)

            result = agent.process_transaction(
                transaction_id=selected_tx_id,
                policy_approved=policy_approved,
                actor_role=role,
                digital_key=digital_key or None,
            )
            st.session_state["mcp_result"] = result

    with reset_col:
        if st.button("Clear Result"):
            st.session_state.pop("mcp_result", None)

    st.subheader("Tool Result")
    result = st.session_state.get("mcp_result")
    if not result:
        st.info("Run an MCP action to see the result.")
    else:
        if result.get("ok"):
            st.success(result.get("message", "Tool call succeeded"))
        else:
            st.error(result.get("error", "Tool call failed"))
        st.json(result)

    st.subheader("Ledger Snapshot")
    st.dataframe(ledger.list_transactions(), use_container_width=True)

    st.subheader("MCP Audit Log")
    if not mcp_server.audit_log:
        st.info("No tool calls logged yet.")
    else:
        st.dataframe(mcp_server.audit_log, use_container_width=True)

    st.subheader("Quick RBAC Check")
    sample_amount = st.number_input("Check amount", min_value=0.0, value=12000.0, step=100.0)
    allowed, reason = RBACPolicy.can_approve(role=role, amount=Decimal(str(sample_amount)), digital_key=digital_key or None)
    st.write({"allowed": allowed, "reason": reason})


if __name__ == "__main__":
    main()
