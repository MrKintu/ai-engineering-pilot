import sys
import os
from typing import Dict, Any, Optional, TypedDict, List, Annotated
import operator
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, AIMessage

# Add parent directory to path for logger_config
sys.path.append(str(Path(__file__).parents[1]))
from logger_config import get_logger

# Load environment variables from .env file in root directory
load_dotenv()
env = os.environ

# Set up logger
logger = get_logger(__name__)

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
    logger.info(f"Checking policy for receipt: {receipt_data.get('id', 'unknown')} with role: {role}")
    logger.debug(f"Receipt category: {receipt_data.get('category')}, amount: ${receipt_data.get('total')}")
    
    verdict = policy_retriever.check_compliance(receipt_data, role)
    
    if verdict.approved:
        logger.info(f"Policy check approved: {verdict.reason}")
    else:
        logger.warning(f"Policy check denied: {verdict.reason}")
    
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
    logger.info("--- [Node: Planner] Starting planning phase ---")
    logger.debug(f"Current state: receipt_id={state.get('receipt_id')}, next_step={state.get('next_step')}")
    
    if not state.get('receipt_data'):
        logger.info("No receipt data found, retrieving receipt")
        receipt = get_receipt_tool(state['receipt_id'])
        return {"receipt_data": receipt, "next_step": "check_policy"}
    
    if not state.get('verdict'):
        logger.info("No verdict found, proceeding to policy check")
        return {"next_step": "check_policy"}
    
    logger.info("Verdict exists, proceeding to critic")
    return {"next_step": "critic"}

def executor_node(state: AuditState):
    logger.info("--- [Node: Executor] Starting execution phase ---")
    logger.debug(f"Next step: {state.get('next_step')}")
    
    if state['next_step'] == "check_policy":
        logger.info("Executing policy check")
        receipt = state['receipt_data']
        verdict = check_policy_tool(receipt)
        return {"verdict": verdict}
    
    logger.warning("Unknown next step in executor")
    return {}

def critic_node(state: AuditState):
    logger.info("--- [Node: Critic] Starting evaluation phase ---")
    verdict = state.get('verdict')
    
    if not verdict:
        logger.error("No verdict found in state")
        return {"status": "error"}
    
    receipt_total = state['receipt_data'].get('total', 0)
    logger.debug(f"Evaluating verdict: approved={verdict.get('approved')}, total=${receipt_total}")
    
    if verdict['approved']:
        if receipt_total > 1000:
            logger.warning(f"High-value approved receipt flagged for human review: ${receipt_total}")
            return {"status": "flagged_for_human"}
        logger.info(f"Receipt approved: ${receipt_total}")
        return {"status": "approved"}
    else:
        logger.warning(f"Receipt denied: {verdict.get('reason')}")
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
logger.info("Starting agentic workflow tests")

print("\n>>> TEST 1: R001 (Should be Approved)")
logger.info("Test 1: Processing receipt R001 (expected: approved)")
res1 = app.invoke({"receipt_id": "R001", "messages": [], "status": "pending", "receipt_data": {}, "verdict": None})
logger.info(f"Test 1 result: {res1['status']}")
print(f"Result: {res1['status']}")

print("\n>>> TEST 2: R003 (Should be Flagged)")
logger.info("Test 2: Processing receipt R003 (expected: flagged_for_human)")
res2 = app.invoke({"receipt_id": "R003", "messages": [], "status": "pending", "receipt_data": {}, "verdict": None})
logger.info(f"Test 2 result: {res2['status']}")
print(f"Result: {res2['status']}")

if res1['status'] == 'approved' and res2['status'] == 'flagged_for_human':
    logger.info("✓ All tests passed successfully")
    print("\n✓ TESTS PASSED")
else:
    logger.error(f"✗ Tests failed - R001: {res1['status']}, R003: {res2['status']}")
    print("\n✗ TESTS FAILED")
