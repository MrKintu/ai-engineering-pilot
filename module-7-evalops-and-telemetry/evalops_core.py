from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import random
from typing import Any, Dict, List, Tuple

# Add parent directory to path for logger_config
sys.path.append(str(Path(__file__).parents[1]))
from logger_config import get_logger

# Set up logger
logger = get_logger(__name__)


@dataclass
class ReceiptCase:
    case_id: str
    category: str
    total: Decimal
    has_receipt: bool
    suspicious_vendor: bool
    employee_role: str
    ground_truth_approved: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "total": str(self.total),
            "has_receipt": self.has_receipt,
            "suspicious_vendor": self.suspicious_vendor,
            "employee_role": self.employee_role,
            "ground_truth_approved": self.ground_truth_approved,
        }


class SnapAuditPolicyModel:
    """Simple deterministic policy model variants for EvalOps demos."""

    def __init__(self, variant: str = "baseline"):
        self.variant = variant
        logger.info(f"Initialized SnapAuditPolicyModel with variant {variant}")

    def predict(self, case: ReceiptCase) -> Tuple[bool, str]:
        logger.info(f"Predicting approval for case {case.case_id}: {case.category} amount=${case.total}")
        
        # Baseline rules
        if not case.has_receipt:
            logger.warning(f"Case {case.case_id} denied: missing receipt")
            return False, "Denied: missing receipt"
        if case.suspicious_vendor:
            logger.warning(f"Case {case.case_id} flagged: suspicious vendor")
            return False, "Denied: suspicious vendor"

        # Regression variant: friendlier prompt behavior over-approves borderline spend.
        if self.variant == "friendly_regression":
            if case.category == "Meal" and case.total <= Decimal("80"):
                logger.info(f"Case {case.case_id} approved: friendly flexibility for meal claims")
                return True, "Approved: friendly flexibility for meal claims"
            if case.category == "Client Dinner" and case.total <= Decimal("220"):
                logger.info(f"Case {case.case_id} approved: friendly flexibility for client relationship spend")
                return True, "Approved: friendly flexibility for client relationship spend"

        meal_limit = Decimal("25")
        if case.employee_role == "Vice President":
            meal_limit = Decimal("50")

        if case.category in {"Meal", "Coffee"} and case.total > meal_limit:
            logger.warning(f"Case {case.case_id} denied: exceeds meal limit {meal_limit}")
            return False, f"Denied: exceeds meal limit {meal_limit}"

        if case.category == "Client Dinner" and case.total > Decimal("150") and case.employee_role != "Vice President":
            logger.warning(f"Case {case.case_id} denied: exceeds client dinner limit")
            return False, "Denied: exceeds client dinner limit"

        logger.info(f"Case {case.case_id} approved: policy compliant")
        return True, "Approved: policy compliant"


class TelemetryCollector:
    def __init__(self):
        logger.info("Initializing TelemetryCollector")
        self.events: List[Dict[str, Any]] = []

    def log(self, case_id: str, step: str, detail: str):
        logger.debug(f"Logging telemetry for case {case_id}: {step} - {detail}")
        self.events.append(
            {
                "time": datetime.now(timezone.utc).isoformat(timespec="seconds").replace('+00:00', 'Z'),
                "case_id": case_id,
                "step": step,
                "detail": detail,
            }
        )

    def get_event_count(self) -> int:
        logger.debug(f"Getting event count: {len(self.events)}")
        return len(self.events)


def make_golden_dataset(size: int = 100, seed: int = 42) -> List[ReceiptCase]:
    logger.info(f"Creating golden dataset with {size} cases (seed: {seed})")
    rnd = random.Random(seed)
    categories = ["Coffee", "Meal", "Client Dinner", "Travel", "Office Supplies"]
    roles = ["Employee", "Manager", "Vice President"]

    cases: List[ReceiptCase] = []
    for i in range(1, size + 1):
        category = rnd.choice(categories)
        role = rnd.choice(roles)

        base = {
            "Coffee": rnd.uniform(3, 15),
            "Meal": rnd.uniform(10, 80),
            "Client Dinner": rnd.uniform(40, 250),
            "Travel": rnd.uniform(20, 900),
            "Office Supplies": rnd.uniform(5, 600),
        }[category]

        has_receipt = rnd.random() > 0.05
        suspicious_vendor = rnd.random() < 0.05
        total = Decimal(str(round(base, 2)))

        # Ground truth uses strict baseline model behavior.
        ground_truth_model = SnapAuditPolicyModel(variant="baseline")
        temp_case = ReceiptCase(
            case_id=f"C{i:03d}",
            category=category,
            total=total,
            has_receipt=has_receipt,
            suspicious_vendor=suspicious_vendor,
            employee_role=role,
            ground_truth_approved=True,
        )
        gt, _ = ground_truth_model.predict(temp_case)
        temp_case.ground_truth_approved = gt
        cases.append(temp_case)
    
    logger.info(f"Generated {len(cases)} test cases")
    return cases


def evaluate_model(
    cases: List[ReceiptCase],
    model: SnapAuditPolicyModel,
    telemetry: TelemetryCollector,
) -> Dict[str, Any]:
    logger.info(f"Starting model evaluation for {len(cases)} cases with model variant: {model.variant}")
    correct = 0
    failures: List[Dict[str, Any]] = []
    faithfulness_scores: List[float] = []
    relevance_scores: List[float] = []

    for case in cases:
        telemetry.log(case.case_id, "start", f"Evaluating {case.category} amount={case.total}")
        pred, reason = model.predict(case)

        # Proxy faithfulness: if denied for policy reasons when ground truth deny, high score.
        faithfulness = 1.0 if (pred == case.ground_truth_approved) else 0.0
        # Proxy relevance: reason should mention key topic words.
        key_words = ["approved", "denied", "limit", "receipt", "vendor", "policy"]
        relevance = 1.0 if any(w in reason.lower() for w in key_words) else 0.5

        faithfulness_scores.append(faithfulness)
        relevance_scores.append(relevance)

        if pred == case.ground_truth_approved:
            correct += 1
            telemetry.log(case.case_id, "result", f"correct prediction: {pred}")
            logger.debug(f"Case {case.case_id}: correct prediction ({pred})")
        else:
            fail = {
                "case": case.to_dict(),
                "predicted_approved": pred,
                "reason": reason,
                "ground_truth_approved": case.ground_truth_approved,
            }
            failures.append(fail)
            telemetry.log(case.case_id, "result", f"mismatch prediction: {pred} vs {case.ground_truth_approved}")
            logger.warning(f"Case {case.case_id}: mismatch prediction - predicted {pred}, expected {case.ground_truth_approved}")

    total = len(cases)
    accuracy = correct / total if total else 0.0
    faithfulness_avg = sum(faithfulness_scores) / total if total else 0.0
    relevance_avg = sum(relevance_scores) / total if total else 0.0

    logger.info(f"Evaluation complete: accuracy={accuracy:.4f}, faithfulness={faithfulness_avg:.4f}, relevance={relevance_avg:.4f}")
    
    return {
        "total_cases": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "faithfulness": round(faithfulness_avg, 4),
        "answer_relevance": round(relevance_avg, 4),
        "failures": failures,
    }
