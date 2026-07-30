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

Tax-aware: the model also detects a tax/IVA/impuestos amount when the
receipt shows one, and that amount is prorated proportionally into the
returned item prices before this module ever returns — so `items.price`
already represents what the group owes for that item, tax included. The
original detected tax amount survives unchanged on `ExtractionResult.
tax_amount` purely for transparency (e.g. "IVA detected: X, already
included proportionally above"); it is never re-applied elsewhere and the
balance math in `schema.sql`'s views is untouched.

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
address, GSTIN), the order/invoice metadata, subtotal, total, due, and any \
footer text. Do not turn tax/IVA/impuestos lines into items — they are \
handled separately by the "tax_amount" field described below.

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

Also look for a tax/IVA/impuestos line (e.g. "IVA", "GST", "CGST/SGST", \
"Impuestos", "Tax"). Receipts show this in different ways: as a plain \
absolute amount (e.g. "IVA 13.50"), or as a percentage row that already \
prints its own computed amount in a separate column (e.g. "Descuento / \
%IVA 10% 13,50€ / Total más impuestos"). In either case, read the \
already-printed absolute amount for "tax_amount" — do NOT calculate a \
percentage yourself. If the receipt shows no tax/IVA/impuestos line at \
all, return "tax_amount": 0.0.

Respond with ONLY a JSON object (no markdown, no code fences, no \
commentary) with this exact shape:

{
  "items": [
    {"description": "...", "price": 0.0, "quantity": 1},
    ...
  ],
  "receipt_total": 0.0,
  "tax_amount": 0.0
}

"receipt_total" is the final total printed on the receipt (the amount \
the customer is charged), used only as a sanity-check reference — it is \
NOT the sum of the item prices, since it also includes tax. "tax_amount" \
is the tax/IVA/impuestos amount described above, read directly off the \
receipt, or 0.0 if no such line is shown.
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
    # The tax/IVA/impuestos amount as detected on the receipt (0.0 if none
    # was shown). Kept at its original, un-prorated value even after
    # `_apply_tax_proration` folds it into `items[*].price` — the frontend
    # uses it purely for transparency ("IVA detected: X, already included
    # proportionally above").
    tax_amount: float = Field(ge=0, allow_inf_nan=False, default=0.0)
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


def _apply_tax_proration(result: ExtractionResult) -> None:
    """
    Fold the detected tax amount proportionally into `result.items[*].price`
    so each item's price already represents what the group actually owes
    for it, tax included — the balance views in `schema.sql` sum item
    prices directly and have no separate notion of tax, so the tax has to
    live inside the item prices themselves rather than as its own line.

    `result.tax_amount` itself is left untouched (see its docstring) —
    only the item prices are mutated here.

    No-op when `tax_amount` is 0 (no tax detected): item prices are left
    byte-for-byte as extracted, so untaxed receipts behave exactly as
    before this change.

    Otherwise, every item's price is scaled up by the same factor
    `1 + tax_amount / items_sum`, except the last item, whose price instead
    absorbs whatever rounding drift is left over so that the prorated
    items sum EXACTLY to `items_sum + tax_amount` (a "largest remainder"
    trick) — this matters because `_apply_total_warnings` (run right after
    this) sanity-checks that sum against `receipt_total`.
    """
    if result.tax_amount <= 0:
        return

    items_sum = sum(item.price for item in result.items)
    target_total = items_sum + result.tax_amount
    factor = 1 + result.tax_amount / items_sum

    running_sum = 0.0
    for item in result.items[:-1]:
        item.price = round(item.price * factor, 2)
        running_sum += item.price

    result.items[-1].price = round(target_total - running_sum, 2)


def _apply_total_warnings(result: ExtractionResult) -> None:
    """
    Flag (but never block on) a suspicious mismatch between the sum of item
    prices and the receipt total.

    Runs AFTER `_apply_tax_proration`, so by this point `items_sum` is
    already tax-inclusive whenever a tax amount was detected — both sides
    of this comparison are meant to represent the same tax-inclusive final
    amount, and are expected to be close. A large gap below the total now
    signals a genuinely missing item or a misread/undetected tax, not the
    tax itself (unlike before this fix, when the sum was always expected
    to sit meaningfully below the total). The "too low" tolerance is
    therefore tightened from the old 70% (which existed specifically to
    tolerate the always-missing tax portion) to 90%, leaving headroom only
    for minor rounding/model imprecision.
    """
    items_sum = sum(item.price for item in result.items)
    tolerance = 0.01

    if items_sum > result.receipt_total + tolerance:
        result.warnings.append(
            "Item prices sum to more than the receipt total "
            f"({items_sum:.2f} > {result.receipt_total:.2f}); "
            "please double-check the amounts before saving."
        )
    elif items_sum < 0.9 * result.receipt_total:
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

    Any detected tax/IVA/impuestos amount is prorated proportionally into
    the returned item prices (see `_apply_tax_proration`) before this
    function returns, so `items.price` is already what the group owes,
    tax included — no separate "tax" line ever needs to be assigned to
    anyone. The original detected amount is preserved, unprorated, on
    `ExtractionResult.tax_amount` for display purposes only.

    A mismatch between the (now tax-inclusive) sum of item prices and
    `receipt_total` is reported via `ExtractionResult.warnings`, not
    raised as an error — the human reviewer always makes the final call.
    """
    if not os.path.isfile(image_path):
        raise ExtractionError(
            f"Receipt image not found at '{image_path}'. "
            "Please use manual item capture."
        )

    raw_json = _call_openai(image_path)
    result = _parse_and_validate(raw_json)
    _apply_tax_proration(result)
    _apply_total_warnings(result)
    return result
