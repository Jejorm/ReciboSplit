"""
Phase 2, Task 2 — production receipt extractor and its Pydantic data contract.

Graduates the tuned prompt from `vision_extract_experiment.py` (Task 1) into
a reusable module the FastAPI extraction endpoint (Task 3) can call.

Strictly additive and isolated from Phase 1: this module does NOT import
`db.py`, `main.py`, or `services.py`, and does NOT open any Turso connection.
It only reads a local image file and calls the OpenAI API, then returns a
validated, in-memory result. It never persists anything — saving only
happens through the existing Phase 1 item-capture endpoints, after a human
reviews the proposed items.

Requires OPENAI_API_KEY in .env (loaded via python-dotenv).
"""

import base64
import json
import mimetypes
import os

import httpx
from dotenv import load_dotenv
from openai import APITimeoutError, OpenAI
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

MODEL = "gpt-5.6-luna"

# The openai SDK default is httpx.Timeout(600, connect=5.0) with 2 automatic
# retries — a stalled-but-connected API could leave a user staring at
# "Extracting..." for close to 20 minutes. We bound the read/write/pool
# budget tightly and keep the SDK's own fast connect timeout (a bare float
# would instead widen connect to the same value, making an unreachable host
# slower to fail than before). With max_retries=1 there are 2 attempts, so a
# fully stalled API can still take up to ~2 x REQUEST_TIMEOUT_SECONDS plus
# backoff before the user gets the timeout message — bounded, unlike the
# SDK default's ~20 minutes.
REQUEST_TIMEOUT_SECONDS = 60.0
CONNECT_TIMEOUT_SECONDS = 5.0

# MIME types OpenAI's vision input accepts. Extensions mapping to any other
# known type (e.g. .heic, .pdf) are rejected before calling the API; unknown
# extensions fall back to "image/jpeg" (uploaded receipts overwhelmingly
# arrive as jpeg/jpg, and the API only needs a plausible image/* value).
_SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_DEFAULT_MIME_TYPE = "image/jpeg"

PROMPT = """You are reading a photo of a retail receipt.

Extract only the purchased line items — ignore the header (store name, \
address, GSTIN), the order/invoice metadata, subtotal, tax lines \
(CGST/SGST/GST), total, due, and any footer text.

Each line item on the receipt may embed a leading quantity in its own \
description text (e.g. "1 Reg HT PM Capsicum" means quantity 1). Some \
receipts print the same item on two separate lines instead of merging \
them into one line with quantity 2 (e.g. "1 Reg HT PM Gold Corn" \
appearing twice at 199.00 each) — in that case, merge them into a \
single item with quantity 2 and keep price as the line total for that \
combined quantity (398.00), not the total quantity split unevenly. Only \
merge lines with an identical description and identical unit price; if \
descriptions or prices differ even slightly, keep them as separate items.

For each distinct item, return:
- "description": a clean human-readable name for the item, WITHOUT the \
leading quantity number (e.g. "Reg HT PM Capsicum", not "1 Reg HT PM \
Capsicum")
- "price": the line total for that item as printed on the receipt, as a \
number (if you merged duplicate lines, sum their prices)
- "quantity": the integer quantity for that item (merge duplicate lines \
into one item with quantity > 1 as described above; otherwise usually 1)

Respond with ONLY a JSON object (no markdown, no code fences, no \
commentary) with this exact shape:

{
  "items": [
    {"description": "...", "price": 0.0, "quantity": 1},
    ...
  ],
  "receipt_total": 0.0
}

"receipt_total" is the final total printed on the receipt (the amount \
the customer is charged), used only as a sanity-check reference — it is \
NOT the sum of the item prices, since it also includes tax.
"""


class ExtractionError(Exception):
    """
    Raised for every extraction failure mode: an unreadable image, an
    OpenAI API/network error, malformed or non-JSON model output, or
    output that fails the Pydantic contract below.

    The message is written to be safe to show directly to an end user
    (the frontend uses it to explain why manual capture is needed).
    """


class ExtractedItem(BaseModel):
    """One proposed line item, shaped to map directly onto the `items` table."""

    description: str = Field(min_length=1)
    # allow_inf_nan=False: json.loads accepts the literal `Infinity`, which
    # passes gt=0 and would be serialized as `null` by FastAPI's encoder,
    # breaking the non-nullable float promise in the OpenAPI contract.
    price: float = Field(gt=0, allow_inf_nan=False)
    quantity: int = Field(ge=1, default=1)


class ExtractionResult(BaseModel):
    """
    The full proposed extraction for one receipt image.

    `warnings` is populated by our own post-extraction validation (e.g. a
    total mismatch), never by the model itself. A non-empty `warnings`
    list is a signal for the human reviewer, not a reason to discard the
    data — the human always decides.
    """

    items: list[ExtractedItem] = Field(min_length=1)
    receipt_total: float = Field(gt=0, allow_inf_nan=False)
    warnings: list[str] = Field(default_factory=list)


def _guess_mime_type(image_path: str) -> str:
    """Infer the image MIME type from the file extension, defaulting to jpeg.

    Extensions that map to a known type the vision API does NOT accept
    (e.g. .heic from iPhone photos, .pdf — both allowed by the Phase 1
    upload endpoint) are rejected up front with an honest message instead
    of being mislabeled as jpeg and failing upstream with a generic error.
    Unknown/missing extensions still default to jpeg.
    """
    guessed_type, _ = mimetypes.guess_type(image_path)
    if guessed_type is None:
        return _DEFAULT_MIME_TYPE
    if guessed_type not in _SUPPORTED_MIME_TYPES:
        raise ExtractionError(
            "This file format is not supported by automatic extraction "
            "(supported: JPEG, PNG, WEBP, GIF). Please use manual item "
            "capture."
        )
    return guessed_type


def _encode_image_b64(image_path: str) -> str:
    """Read and base64-encode the image file. Raises ExtractionError if unreadable."""
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except OSError as exc:
        raise ExtractionError(
            f"Could not read receipt image at '{image_path}'. "
            "Please retry with manual item capture."
        ) from exc


def _call_openai(image_path: str) -> str:
    """Call the OpenAI vision model and return the raw response text."""
    mime_type = _guess_mime_type(image_path)
    b64_image = _encode_image_b64(image_path)

    try:
        client = OpenAI(
            timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS),
            max_retries=1,
        )
        response = client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_image}"
                            },
                        },
                    ],
                }
            ],
        )
    except APITimeoutError as exc:
        # Caught before the broad except below so a stalled API gets its
        # own distinct, user-safe message instead of the generic
        # "unavailable" one.
        raise ExtractionError(
            "The receipt extraction service took too long to respond. "
            "Try again, or use manual item capture."
        ) from exc
    except Exception as exc:
        # Covers every openai SDK exception: auth errors, rate limits,
        # timeouts, connection errors, etc. We don't rely on the caller
        # (or ourselves) enumerating the openai package's exception
        # hierarchy — any failure here means "fall back to manual capture".
        raise ExtractionError(
            "The receipt extraction service is unavailable right now. "
            "Please use manual item capture."
        ) from exc

    content = response.choices[0].message.content
    if not content:
        raise ExtractionError(
            "The receipt extraction service returned an empty response. "
            "Please use manual item capture."
        )
    return content


def _parse_and_validate(raw_json: str) -> ExtractionResult:
    """Parse the model's raw text as JSON and validate it against the contract."""
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ExtractionError(
            "The receipt extraction service returned an unreadable response. "
            "Please use manual item capture."
        ) from exc

    try:
        result = ExtractionResult(**payload)
    except (ValidationError, TypeError) as exc:
        raise ExtractionError(
            "The receipt extraction service returned data in an unexpected "
            "format. Please use manual item capture."
        ) from exc

    return result


def _apply_total_warnings(result: ExtractionResult) -> None:
    """
    Flag (but never block on) a suspicious mismatch between the sum of item
    prices and the receipt total. Tax-aware: item prices are pre-tax line
    totals and `receipt_total` is the tax-inclusive amount printed on the
    receipt, so the sum is expected to be somewhat below the total, never
    above it.
    """
    items_sum = sum(item.price for item in result.items)
    tolerance = 0.01

    if items_sum > result.receipt_total + tolerance:
        result.warnings.append(
            "Item prices sum to more than the receipt total "
            f"({items_sum:.2f} > {result.receipt_total:.2f}); "
            "please double-check the amounts before saving."
        )
    elif items_sum < 0.7 * result.receipt_total:
        result.warnings.append(
            "Item prices sum to much less than the receipt total "
            f"({items_sum:.2f} vs {result.receipt_total:.2f}); "
            "some line items may be missing."
        )


def extract_receipt_items(image_path: str) -> ExtractionResult:
    """
    Read the receipt image at `image_path`, call the OpenAI vision model,
    and return a validated `ExtractionResult` with proposed items.

    This is a read-only convenience call: it never writes to the database
    and never modifies the image. Any failure (missing/unreadable image,
    API error, malformed output, or a contract violation) is raised as
    `ExtractionError` so the caller can fall back to manual capture.

    A mismatch between the sum of item prices and `receipt_total` is
    reported via `ExtractionResult.warnings`, not raised as an error —
    the human reviewer always makes the final call.
    """
    if not os.path.isfile(image_path):
        raise ExtractionError(
            f"Receipt image not found at '{image_path}'. "
            "Please use manual item capture."
        )

    raw_json = _call_openai(image_path)
    result = _parse_and_validate(raw_json)
    _apply_total_warnings(result)
    return result
