import sys
import os
from typing import Dict, Any, Optional, TypedDict, List, Annotated
import operator
from langchain_core.messages import BaseMessage, AIMessage

# Load OPENAI_API_KEY from repo-root .env if present.
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path) and "OPENAI_API_KEY" not in os.environ:
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "OPENAI_API_KEY":
                os.environ["OPENAI_API_KEY"] = value.strip().strip("'\"")
                break

# Add snapaudit-integrated to path
sys.path.append("../snapaudit-integrated")

try:
    from policy_retriever import PolicyRetriever, PolicyVerdict
    print("✓ Successfully imported PolicyRetriever")
except ImportError:
    print("⚠ Could not import PolicyRetriever.")
    sys.exit(1)

# Mock Tools for Testing
class MockPolicyRetriever:
    def check_compliance(self, receipt_data, role):
        # Simple mock logic
        total = receipt_data.get('total', 0)
        approved = total < 100
        return type('obj', (object,), {
            'approved': approved, 
            'reason': 'Mock reason', 
            'citations': ['Mock citation']
        })

# Use mock if real one fails or for speed, but let's try to instantiate 
# (assuming Qdrant is up, which it is)
try:
    policy_pdf_path = "../snapaudit-integrated/sample_expense_policy.pdf"
    if os.path.exists(policy_pdf_path):
        policy_retriever = PolicyRetriever(policy_pdf_path)
    else:
        print("PDF not found, using Mock")
        policy_retriever = MockPolicyRetriever()
except Exception as e:
    print(f"Failed to init PolicyRetriever ({e}), using Mock")
    policy_retriever = MockPolicyRetriever()

def check_policy_tool(receipt_data: Dict[str, Any], role: str = "Employee") -> Dict[str, Any]:
    print(f"--- [Tool: CheckPolicy] Checking {receipt_data.get('category')} for ${receipt_data.get('total')} ---")
    verdict = policy_retriever.check_compliance(receipt_data, role)
    return {
        "approved": verdict.approved,
        "reason": verdict.reason,
        "citations": verdict.citations
    }

def get_receipt_tool(receipt_id: str) -> Dict[str, Any]:
    MOCK_RECEIPTS = {
        "R001": {"id": "R001", "total": 20.00, "category": "Lunch", "merchant": "Sandwich Shop", "date": "2024-01-15"},
        "R003": {"id": "R003", "total": 5000.00, "category": "Office Supplies", "merchant": "Apple Store", "date": "2024-01-17"},
    }
    return MOCK_RECEIPTS.get(receipt_id, {})

# Graph Logic
from langgraph.graph import StateGraph, END

class AuditState(TypedDict):
    receipt_id: str
    receipt_data: Dict[str, Any]
    verdict: Optional[Dict[str, Any]]
    status: str
    messages: Annotated[List[BaseMessage], operator.add]
    next_step: str

def planner_node(state: AuditState):
    print("--- [Node: Planner] ---")
    if not state.get('receipt_data'):
        receipt = get_receipt_tool(state['receipt_id'])
        return {"receipt_data": receipt, "next_step": "check_policy"}
    if not state.get('verdict'):
        return {"next_step": "check_policy"}
    return {"next_step": "critic"}

def executor_node(state: AuditState):
    print("--- [Node: Executor] ---")
    if state['next_step'] == "check_policy":
        receipt = state['receipt_data']
        verdict = check_policy_tool(receipt)
        return {"verdict": verdict}
    return {}

def critic_node(state: AuditState):
    print("--- [Node: Critic] ---")
    verdict = state.get('verdict')
    if not verdict:
        return {"status": "error"}
    
    receipt_total = state['receipt_data'].get('total', 0)
    if verdict['approved']:
        if receipt_total > 1000:
            return {"status": "flagged_for_human"}
        return {"status": "approved"}
    else:
        return {"status": "denied"}

# Build Graph
workflow = StateGraph(AuditState)
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)
workflow.add_node("critic", critic_node)
workflow.set_entry_point("planner")

def route_planner(state):
    return "executor" if state.get("next_step") == "check_policy" else "critic"

def route_critic(state):
    return END if state.get("status") in ["approved", "denied", "flagged_for_human"] else "planner"

workflow.add_conditional_edges("planner", route_planner, {"executor": "executor", "critic": "critic"})
workflow.add_edge("executor", "planner")
workflow.add_conditional_edges("critic", route_critic, {END: END, "planner": "planner"})

app = workflow.compile()

# Test
print("\n>>> TEST 1: R001 (Should be Approved)")
res1 = app.invoke({"receipt_id": "R001", "messages": [], "status": "pending", "receipt_data": {}, "verdict": None})
print(f"Result: {res1['status']}")

print("\n>>> TEST 2: R003 (Should be Flagged)")
res2 = app.invoke({"receipt_id": "R003", "messages": [], "status": "pending", "receipt_data": {}, "verdict": None})
print(f"Result: {res2['status']}")

if res1['status'] == 'approved' and res2['status'] == 'flagged_for_human':
    print("\n✓ TESTS PASSED")
else:
    print("\n✗ TESTS FAILED")
