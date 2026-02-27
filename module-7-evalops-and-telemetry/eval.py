from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from evalops_core import make_golden_dataset, SnapAuditPolicyModel, TelemetryCollector, evaluate_model


def main() -> int:
    threshold = float(os.getenv("EVAL_ACCURACY_THRESHOLD", "0.99"))
    variant = os.getenv("MODEL_VARIANT", "baseline")

    cases = make_golden_dataset(size=100, seed=42)
    model = SnapAuditPolicyModel(variant=variant)
    telemetry = TelemetryCollector()

    metrics = evaluate_model(cases, model, telemetry)

    summary = {
        "model_variant": variant,
        "threshold": threshold,
        **{k: metrics[k] for k in ["total_cases", "correct", "accuracy", "faithfulness", "answer_relevance"]},
    }

    print(json.dumps(summary, indent=2))

    out_dir = Path(".")
    (out_dir / "eval_results.json").write_text(json.dumps(metrics, indent=2))
    (out_dir / "telemetry_log.json").write_text(json.dumps(telemetry.events, indent=2))

    if metrics["accuracy"] < threshold:
        print(f"\n❌ Blocking deployment: accuracy {metrics['accuracy']:.4f} < threshold {threshold:.4f}")
        return 1

    print(f"\n✅ Eval gate passed: accuracy {metrics['accuracy']:.4f} >= threshold {threshold:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
