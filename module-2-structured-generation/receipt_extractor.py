"""SnapAudit Receipt Extraction Engine.

Provides Ollama and OpenAI extractors with a shared self-healing retry loop.
Imported by streamlit_app.py for the interactive UI.
"""

import base64
import json
import os
import sys
import textwrap
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional, Tuple, Union

import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError, SkipValidation

# Add parent directory to path for logger_config
sys.path.append(str(Path(__file__).parents[1]))
from logger_config import get_logger

# Set up logger
logger = get_logger(__name__)

# Load environment variables from .env file in root directory
load_dotenv()
env = os.environ


# ── Data Contract ───────────────────────────────────────────────────
class Receipt(BaseModel):
    """Strict data contract for SnapAudit receipts (mirrors SQL schema)."""

    # arbitrary_types_allowed: lets Pydantic handle Decimal without complaints
    model_config = ConfigDict(arbitrary_types_allowed=True)

    merchant: str = Field(..., description="Name of the merchant or vendor")
    date: SkipValidation[Union[date, None]] = Field(
        default=None,
        description="Transaction date in ISO format YYYY-MM-DD, if present.",
    )
    currency: str = Field(..., description="Three-letter currency code, e.g. 'USD'.")
    # Decimal, not float — avoids floating-point rounding in financial data
    total: SkipValidation[Decimal] = Field(..., description="Total amount charged, as a decimal.")
    tax: SkipValidation[Union[Decimal, None]] = Field(
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
    """Self-healing extraction engine with a shared retry loop.

    Subclasses override `_call_llm(prompt)` to plug in any LLM backend.
    """

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries

    # ── Subclasses must implement this ──────────────────────────────
    def _call_llm(self, prompt: str) -> str:
        raise NotImplementedError

    # ── Clean JSON output by removing markdown code blocks and extra whitespace ───────────────
    def _clean_json_output(self, raw: str) -> str:
        """Clean JSON output by removing markdown code blocks and extra whitespace."""
        raw = raw.strip()
        
        # Remove markdown code blocks if present
        if raw.startswith('```json'):
            raw = raw[7:]  # Remove ```json
        elif raw.startswith('```'):
            raw = raw[3:]   # Remove ```
            
        if raw.endswith('```'):
            raw = raw[:-3]  # Remove closing ```
            
        return raw.strip()

    def _convert_decimal_field(self, value: str) -> Decimal:
        """Convert string to Decimal, handling conversion errors."""
        try:
            return Decimal(value)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert '{value}' to Decimal")

    def _convert_date_field(self, value: str) -> date:
        """Convert string to date, handling conversion errors."""
        try:
            from datetime import datetime
            return datetime.strptime(value, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert '{value}' to date")

    def _convert_total_field(self, converted: dict) -> None:
        """Convert total field from string to Decimal."""
        if 'total' in converted and isinstance(converted['total'], str):
            try:
                converted['total'] = self._convert_decimal_field(converted['total'])
            except ValueError:
                pass  # Keep original value if conversion fails

    def _convert_tax_field(self, converted: dict) -> None:
        """Convert tax field from string to Decimal or None."""
        if 'tax' in converted and converted['tax'] is not None:
            if isinstance(converted['tax'], str):
                try:
                    converted['tax'] = self._convert_decimal_field(converted['tax'])
                except ValueError:
                    converted['tax'] = None

    def _convert_date_field_in_obj(self, converted: dict) -> None:
        """Convert date field from string to date object or None."""
        if 'date' in converted and converted['date'] is not None:
            if isinstance(converted['date'], str):
                try:
                    converted['date'] = self._convert_date_field(converted['date'])
                except ValueError:
                    converted['date'] = None

    def _convert_types(self, obj: dict) -> dict:
        """Convert string types to proper Python types for Pydantic validation."""
        converted = obj.copy()
        
        # Convert each field using dedicated methods
        self._convert_total_field(converted)
        self._convert_tax_field(converted)
        self._convert_date_field_in_obj(converted)
        
        return converted

    # ── Parse + validate against Pydantic schema ───────────────
    def _parse_and_validate(self, raw: str) -> Tuple[Receipt, dict]:
        """JSON-parse raw LLM output and validate against `Receipt`."""
        logger.debug(f"Raw LLM output: {repr(raw)}")
        cleaned_raw = self._clean_json_output(raw)
        logger.debug(f"Cleaned output: {repr(cleaned_raw)}")
        obj = json.loads(cleaned_raw)
        
        # Convert types before validation
        converted_obj = self._convert_types(obj)
        logger.debug(f"Converted object: {converted_obj}")
        
        receipt = Receipt.model_validate(converted_obj)
        logger.info("Receipt validation successful")
        return receipt, obj

    # ── Self-healing retry loop ────────────────────────────────────
    def extract(self, receipt_text: str) -> Receipt:
        """Extract a `Receipt` from messy OCR text, retrying on validation errors."""
        logger.info(f"Starting receipt extraction: {receipt_text[:50]}...")
        prompt = build_receipt_prompt(receipt_text)
        last_error: str | None = None
        raw: str = ""

        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Extraction attempt {attempt}/{self.max_retries}")
            
            if attempt == 1:
                raw = self._call_llm(prompt)
            else:
                logger.warning(f"Retry attempt {attempt} due to validation error")
                # Feed the error + bad output back so the model can self-correct
                retry_prompt = (
                    f"The JSON you produced did not pass validation.\n"
                    f"Validation error:\n\n{last_error}\n\n"
                    f"Invalid JSON:\n\n{raw}\n\n"
                    f"Respond with a corrected JSON object only."
                )
                raw = self._call_llm(retry_prompt)

            try:
                receipt, _ = self._parse_and_validate(raw)
                logger.info(f"Receipt extraction successful on attempt {attempt}")
                return receipt
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = str(e)
                logger.error(f"Validation failed on attempt {attempt}: {last_error}")
                if attempt == self.max_retries:
                    logger.error(f"Extraction failed after {self.max_retries} attempts")
                    raise RuntimeError(
                        f"Failed after {self.max_retries} attempts. Last error: {last_error}"
                    ) from e

        raise RuntimeError("Unexpected failure in extract()")  # unreachable


# ── Ollama Extractor ────────────────────────────────────────────────
OLLAMA_BASE_URL = env.get("OLLAMA_BASE_URL")
OLLAMA_MODEL = env.get("OLLAMA_MODEL")

class ReceiptExtractorOllama(BaseReceiptExtractor):
    """Ollama-backed extractor — runs entirely on your local machine."""

    def __init__(self, model: str = OLLAMA_MODEL, max_retries: int = 3) -> None:
        super().__init__(max_retries=max_retries)
        self.model = model
        logger.info(f"Initialized Ollama extractor with model: {model}")

    def _call_llm(self, prompt: str) -> str:
        logger.debug(f"Calling Ollama API with model: {self.model}")
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
        output = response.json()["message"]["content"]
        logger.debug(f"Ollama response received: {output[:100]}...")
        return output


# ── OpenAI Extractor ────────────────────────────────────────────────
class ReceiptExtractorOpenAI(BaseReceiptExtractor):
    """OpenAI-backed extractor — supports both text and image inputs."""

    def __init__(self, model: str = "gpt-4o-mini", max_retries: int = 3) -> None:
        super().__init__(max_retries=max_retries)
        self.model = model
        self.client = OpenAI()  # reads OPENAI_API_KEY from env
        logger.info(f"Initialized OpenAI extractor with model: {model}")

    def _call_llm(self, prompt: str) -> str:
        logger.debug(f"Calling OpenAI API with model: {self.model}")
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            top_p=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        output = resp.choices[0].message.content
        logger.debug(f"OpenAI response received: {output[:100]}...")
        return output

    # ── Vision: extract from a receipt image ───────────────────────
    def _call_llm_with_image(
        self, prompt: str, image_b64: str, mime_type: str = "image/png"
    ) -> str:
        """Send a prompt + base64-encoded image to the Vision API."""
        logger.debug(f"Calling OpenAI Vision API with model: {self.model}")
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
        output = resp.choices[0].message.content
        logger.debug(f"OpenAI Vision response received: {output[:100]}...")
        return output

    def extract_from_image(self, image_bytes: bytes, mime_type: str = "image/png") -> Receipt:
        """Extract a Receipt from a receipt image, with self-healing retries."""
        logger.info(f"Starting image extraction ({mime_type})")
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = build_receipt_prompt("[See the attached receipt image]")
        last_error: str | None = None
        raw: str = ""

        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Image extraction attempt {attempt}/{self.max_retries}")
            
            if attempt == 1:
                # First attempt: send image + prompt together
                raw = self._call_llm_with_image(prompt, image_b64, mime_type)
            else:
                logger.warning(f"Image retry attempt {attempt} due to validation error")
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
                logger.info(f"Image extraction successful on attempt {attempt}")
                return receipt
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = str(e)
                logger.error(f"Image validation failed on attempt {attempt}: {last_error}")
                if attempt == self.max_retries:
                    logger.error(f"Image extraction failed after {self.max_retries} attempts")
                    raise RuntimeError(
                        f"Failed after {self.max_retries} attempts. Last error: {last_error}"
                    ) from e

        raise RuntimeError("Unexpected failure in extract_from_image()")


# ── Test Examples ───────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing ReceiptExtractor with Ollama...")
    OLLAMA_MODEL = env.get("OLLAMA_MODEL")
    # Test with Ollama
    extractor = ReceiptExtractorOllama(model=OLLAMA_MODEL, max_retries=3)
    
    messy_ocr = """
    SNAPMART GROCERY
    2026/01/17
    ...
    subtotal   $9.5
    TAX 0.50
    TOTAL approximately $10
    Thank you for shopping!!
    """
    
    try:
        receipt = extractor.extract(messy_ocr)
        print("Validated Receipt:")
        print(receipt)
        print("\nAs dict (SQL-ready):")
        print(receipt.model_dump())
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    print("Testing ReceiptExtractor with OpenAI...")
    
    # Test with OpenAI (if API key is available)
    try:
        oa_extractor = ReceiptExtractorOpenAI(model="gpt-4o-mini", max_retries=3)
        
        messy_ocr2 = """
        CITY CAFE AND BAKERY
        Jan 03 2026
        --
        Latte 4.5
        Muffin 3.25
        Tax   0.64
        Total ten dollars and some cents
        --
        Thank you!
        """
        
        receipt2 = oa_extractor.extract(messy_ocr2)
        print("Validated Receipt (OpenAI):")
        print(receipt2)
        print("\nAs dict (SQL-ready):")
        print(receipt2.model_dump())
    except Exception as e:
        print(f"OpenAI test failed (likely missing API key): {e}")
