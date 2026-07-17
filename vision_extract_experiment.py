"""
Task 1 (Phase 2) — throwaway/experimental script to tune the vision prompt.

Standalone and isolated from Phase 1: does NOT import main.py, db.py,
services.py, or touch schema.sql/frontend/. Does NOT open any Turso
connection — it only reads a local image file and calls the OpenAI API.

This is NOT the final data contract (that's Task 2, with Pydantic
validation) and NOT the FastAPI endpoint (Task 3). It just prints the
raw model output so the prompt can be inspected and iterated on.

Usage:
    uv run python vision_extract_experiment.py [path/to/receipt.jpg]

Requires OPENAI_API_KEY in .env (loaded via python-dotenv, same pattern
already used elsewhere in this project).
"""

import base64
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_IMAGE_PATH = "bills/bill_example.jpg"

MODEL = "gpt-5.6-luna"

PROMPT = """You are reading a photo of a retail receipt (this one is an \
Indian tax invoice from a pizza restaurant, but treat it generically).

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


def encode_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def main() -> None:
    image_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE_PATH

    b64_image = encode_image_b64(image_path)

    client = OpenAI()

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
                            "url": f"data:image/jpeg;base64,{b64_image}"
                        },
                    },
                ],
            }
        ],
    )

    raw_json = response.choices[0].message.content
    print(raw_json)


if __name__ == "__main__":
    main()
