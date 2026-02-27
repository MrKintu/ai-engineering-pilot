from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class Transaction:
    transaction_id: str
    vendor: str
    amount: Decimal
    currency: str
    category: str
    status: str = "pending"  # pending, approved, flagged
    reason: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "vendor": self.vendor,
            "amount": str(self.amount),
            "currency": self.currency,
            "category": self.category,
            "status": self.status,
            "reason": self.reason,
            "updated_at": self.updated_at,
        }


class MockERPLedger:
    """Mock ERP ledger for MCP integration demos."""

    def __init__(self):
        self.transactions: Dict[str, Transaction] = {
            "T1001": Transaction("T1001", "Staples", Decimal("245.50"), "USD", "Office Supplies"),
            "T1002": Transaction("T1002", "Delta Airlines", Decimal("1860.00"), "USD", "Travel"),
            "T1003": Transaction("T1003", "Global Consulting", Decimal("12500.00"), "USD", "Consulting"),
            "T1004": Transaction("T1004", "AWS", Decimal("9800.00"), "USD", "Cloud"),
        }

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        return self.transactions.get(transaction_id)

    def list_transactions(self) -> List[Dict[str, Any]]:
        return [txn.to_dict() for txn in self.transactions.values()]


class RBACPolicy:
    """Role-based control for sensitive ERP actions."""

    HIGH_VALUE_THRESHOLD = Decimal("10000")
    HIGH_VALUE_KEY = "ERP-APPROVE-10K"

    @classmethod
    def can_approve(cls, role: str, amount: Decimal, digital_key: Optional[str]) -> tuple[bool, str]:
        role = role.strip().lower()

        if amount <= cls.HIGH_VALUE_THRESHOLD:
            if role in {"agent", "manager", "finance_admin"}:
                return True, "Allowed: amount under threshold"
            return False, "Denied: role not permitted for approvals"

        # Over threshold: stricter path
        if role != "finance_admin":
            return False, "Denied: only finance_admin can approve transactions over $10k"

        if digital_key != cls.HIGH_VALUE_KEY:
            return False, "Denied: missing/invalid digital key for high-value approval"

        return True, "Allowed: finance_admin with valid digital key"


class ERPConnectorMCPServer:
    """Mock MCP server exposing safe ledger tools."""

    def __init__(self, ledger: MockERPLedger):
        self.ledger = ledger
        self.audit_log: List[Dict[str, Any]] = []

    def _log(self, tool: str, actor_role: str, transaction_id: str, result: str, detail: str):
        self.audit_log.append(
            {
                "time": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "tool": tool,
                "actor_role": actor_role,
                "transaction_id": transaction_id,
                "result": result,
                "detail": detail,
            }
        )

    def get_transaction(self, transaction_id: str) -> Dict[str, Any]:
        txn = self.ledger.get_transaction(transaction_id)
        if not txn:
            return {"ok": False, "error": "Transaction not found"}
        return {"ok": True, "transaction": txn.to_dict()}

    def approve_transaction(
        self,
        transaction_id: str,
        actor_role: str,
        digital_key: Optional[str] = None,
        reason: str = "Policy compliant",
    ) -> Dict[str, Any]:
        txn = self.ledger.get_transaction(transaction_id)
        if not txn:
            self._log("approve_transaction", actor_role, transaction_id, "error", "Transaction not found")
            return {"ok": False, "error": "Transaction not found"}

        allowed, policy_reason = RBACPolicy.can_approve(actor_role, txn.amount, digital_key)
        if not allowed:
            self._log("approve_transaction", actor_role, transaction_id, "denied", policy_reason)
            return {
                "ok": False,
                "error": policy_reason,
                "transaction": txn.to_dict(),
            }

        txn.status = "approved"
        txn.reason = reason
        txn.updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        self._log("approve_transaction", actor_role, transaction_id, "approved", policy_reason)

        return {
            "ok": True,
            "message": "Transaction approved",
            "transaction": txn.to_dict(),
            "policy": policy_reason,
        }

    def flag_fraud(self, transaction_id: str, actor_role: str, reason: str) -> Dict[str, Any]:
        txn = self.ledger.get_transaction(transaction_id)
        if not txn:
            self._log("flag_fraud", actor_role, transaction_id, "error", "Transaction not found")
            return {"ok": False, "error": "Transaction not found"}

        if actor_role.strip().lower() not in {"agent", "manager", "finance_admin"}:
            deny = "Denied: role not permitted to flag transactions"
            self._log("flag_fraud", actor_role, transaction_id, "denied", deny)
            return {"ok": False, "error": deny}

        txn.status = "flagged"
        txn.reason = reason
        txn.updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        self._log("flag_fraud", actor_role, transaction_id, "flagged", reason)

        return {
            "ok": True,
            "message": "Transaction flagged",
            "transaction": txn.to_dict(),
        }


class SnapAuditAgentClient:
    """Minimal client that uses MCP tools to complete ERP actions."""

    def __init__(self, mcp_server: ERPConnectorMCPServer):
        self.server = mcp_server

    def process_transaction(
        self,
        transaction_id: str,
        policy_approved: bool,
        actor_role: str,
        digital_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Read from ERP first
        read_result = self.server.get_transaction(transaction_id)
        if not read_result.get("ok"):
            return read_result

        if policy_approved:
            return self.server.approve_transaction(
                transaction_id=transaction_id,
                actor_role=actor_role,
                digital_key=digital_key,
                reason="Approved by SnapAudit policy flow",
            )

        return self.server.flag_fraud(
            transaction_id=transaction_id,
            actor_role=actor_role,
            reason="Policy engine returned non-compliant",
        )
