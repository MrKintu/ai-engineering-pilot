from __future__ import annotations

import json

from security_middleware import SecurityMiddleware, sample_receipt_notes


def main() -> int:
    middleware = SecurityMiddleware()
    notes = sample_receipt_notes()

    report = {}
    for key, text in notes.items():
        result = middleware.scan_input(text)
        report[key] = result.to_dict()

    fake_llm_output = {
        "status": "approved",
        "note": "User email jane.doe@corp.com used card 4111 1111 1111 1111",
    }
    sanitized_output = middleware.sanitize_output_for_logging(fake_llm_output)

    print("=== Security Scan Report ===")
    print(json.dumps(report, indent=2))
    print("\n=== Sanitized Output ===")
    print(json.dumps(sanitized_output, indent=2))

    # CI-style checks
    assert report["safe"]["allowed"] is True
    assert report["injection"]["allowed"] is False
    assert report["jailbreak"]["allowed"] is False
    assert "[REDACTED_CREDIT_CARD]" in report["pii"]["sanitized_text"]
    assert "[REDACTED_EMAIL]" in sanitized_output["note"]

    print("\n✓ SecurityMiddleware smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
