"""SnapAudit Receipt Extraction Engine.

Provides Ollama and OpenAI extractors with a shared self-healing retry loop.
Imported by streamlit_app.py for the interactive UI.
"""

import base64
import json
import os
import textwrap
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional, Tuple

import requests
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError


# ── Load .env from current or parent directory ──────────────────────
def _load_env() -> None:
    """Search for .env in current and parent dirs, load OPENAI_API_KEY."""
    for search_dir in [Path("."), Path("..")]:
        env_path = search_dir / ".env"
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip('"').strip("'")
                        if not os.getenv(k):
                            os.environ[k] = v
            break


_load_env()


# ── Data Contract ───────────────────────────────────────────────────
class Receipt(BaseModel):
    """Strict data contract for SnapAudit receipts (mirrors SQL schema)."""

    # arbitrary_types_allowed: lets Pydantic handle Decimal without complaints
    model_config = ConfigDict(arbitrary_types_allowed=True)

    merchant: str = Field(..., description="Name of the merchant or vendor")
    date: Optional[date] = Field(
        default=None,
        description="Transaction date in ISO format YYYY-MM-DD, if present.",
    )
    currency: str = Field(..., description="Three-letter currency code, e.g. 'USD'.")
    # Decimal, not float — avoids floating-point rounding in financial data
    total: Decimal = Field(..., description="Total amount charged, as a decimal.")
    tax: Optional[Decimal] = Field(
        default=None, description="Tax amount as a decimal, if inferrable."
    )
    category: str = Field(
        ..., description="High-level category label, e.g. 'Meal', 'Travel'."
    )


# ── Prompt Template ─────────────────────────────────────────────────
def build_receipt_prompt(receipt_text: str) -> str:
    """Build a strict JSON-only extraction prompt for the Receipt schema."""
    return textwrap.dedent(
        f"""
        You are a strict data extraction engine for financial receipts.

        INPUT: Raw OCR text from a receipt.
        OUTPUT: A single JSON object matching this exact schema:

        {{
          \"merchant\": string,                     // required
          \"date\": \"YYYY-MM-DD\" or null,        // optional
          \"currency\": string,                    // required, 3-letter code like \"USD\"
          \"total\": string,                       // required, decimal with 2 places (e.g. \"10.00\")
          \"tax\": string or null,                 // optional, decimal with 2 places
          \"category\": string                     // required, short label like \"Meal\" or \"Travel\"
        }}

        Rules:
        - DO NOT wrap the JSON in backticks or markdown fences.
        - DO NOT include any explanation, comments, or extra keys.
        - Use \"null\" for missing optional fields — never invent values.
        - Normalize currency amounts to two decimal places as strings.

        --- RECEIPT TEXT START ---
        {receipt_text}
        --- RECEIPT TEXT END ---
        """
    ).strip()


# ── Base Extractor (shared retry loop) ──────────────────────────────
class BaseReceiptExtractor:
    """Self-healing extraction engine. Subclasses override `_call_llm()`."""

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries

    def _call_llm(self, prompt: str) -> str:
        raise NotImplementedError

    def _parse_and_validate(self, raw: str) -> Tuple[Receipt, dict]:
        obj = json.loads(raw)
        receipt = Receipt.model_validate(obj)
        return receipt, obj

    def extract(self, receipt_text: str) -> Receipt:
        """Extract a Receipt from messy OCR text, retrying on validation errors."""
        prompt = build_receipt_prompt(receipt_text)
        last_error: str | None = None
        raw: str = ""

        for attempt in range(1, self.max_retries + 1):
            if attempt == 1:
                raw = self._call_llm(prompt)
            else:
                retry_prompt = (
                    f"The JSON you produced did not pass validation.\n"
                    f"Validation error:\n\n{last_error}\n\n"
                    f"Invalid JSON:\n\n{raw}\n\n"
                    f"Respond with a corrected JSON object only."
                )
                raw = self._call_llm(retry_prompt)

            try:
                receipt, _ = self._parse_and_validate(raw)
                return receipt
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = str(e)
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Failed after {self.max_retries} attempts. Last error: {last_error}"
                    ) from e

        raise RuntimeError("Unexpected failure in extract()")


# ── Ollama Extractor ────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"


class ReceiptExtractorOllama(BaseReceiptExtractor):
    """Ollama-backed extractor — runs entirely on your local machine."""

    def __init__(self, model: str = "llama3.1", max_retries: int = 3) -> None:
        super().__init__(max_retries=max_retries)
        self.model = model

    def _call_llm(self, prompt: str) -> str:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0, "top_p": 0.1},
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


# ── OpenAI Extractor ────────────────────────────────────────────────
class ReceiptExtractorOpenAI(BaseReceiptExtractor):
    """OpenAI-backed extractor — supports both text and image inputs."""

    def __init__(self, model: str = "gpt-4.1-mini", max_retries: int = 3) -> None:
        super().__init__(max_retries=max_retries)
        self.model = model
        self.client = OpenAI()  # reads OPENAI_API_KEY from env

    def _call_llm(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            top_p=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content

    # ── Vision: extract from a receipt image ───────────────────────
    def _call_llm_with_image(
        self, prompt: str, image_b64: str, mime_type: str = "image/png"
    ) -> str:
        """Send a prompt + base64-encoded image to the Vision API."""
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            top_p=0.1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}",
                            },
                        },
                    ],
                }
            ],
        )
        return resp.choices[0].message.content

    def extract_from_image(self, image_bytes: bytes, mime_type: str = "image/png") -> Receipt:
        """Extract a Receipt from a receipt image, with self-healing retries."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = build_receipt_prompt("[See the attached receipt image]")
        last_error: str | None = None
        raw: str = ""

        for attempt in range(1, self.max_retries + 1):
            if attempt == 1:
                # First attempt: send image + prompt together
                raw = self._call_llm_with_image(prompt, image_b64, mime_type)
            else:
                # Retries: text-only with error feedback (model already "saw" the image)
                retry_prompt = (
                    f"The JSON you produced did not pass validation.\n"
                    f"Validation error:\n\n{last_error}\n\n"
                    f"Invalid JSON:\n\n{raw}\n\n"
                    f"Respond with a corrected JSON object only."
                )
                raw = self._call_llm_with_image(retry_prompt, image_b64, mime_type)

            try:
                receipt, _ = self._parse_and_validate(raw)
                return receipt
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = str(e)
                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Failed after {self.max_retries} attempts. Last error: {last_error}"
                    ) from e

        raise RuntimeError("Unexpected failure in extract_from_image()")
