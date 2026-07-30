"""
FastAPI application for ReciboSplit (Day 5 scope): participants, events,
image upload, manual item capture, item assignments, and balance reads.
Endpoints call db.py functions only — no SQL is written here.
"""

import os
from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator, Optional, Union

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db
import vision
from services import clear_upload_dir, save_receipt_image, value_error_to_http


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Establish the shared Turso connection and pull from remote once at
    startup, instead of paying that cost on the first request."""
    db.init_db()
    yield


app = FastAPI(title="ReciboSplit API", lifespan=lifespan)

# CORS: the React frontend calls this API cross-origin. Local dev origins are
# always allowed; the deployed Cloudflare Pages origin is added via the
# FRONTEND_ORIGIN env var (set in Render) so this doesn't need a code change
# per environment.
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_frontend_origin = os.environ.get("FRONTEND_ORIGIN")
_allowed_origins = _default_origins + [_frontend_origin] if _frontend_origin else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic models ---------------------------------------------------------


class ParticipantCreate(BaseModel):
    name: str = Field(min_length=1)


class IdResponse(BaseModel):
    id: int


class ParticipantOut(BaseModel):
    id: int
    name: str
    created_at: str


class EventCreate(BaseModel):
    name: str = Field(min_length=1)
    event_date: Optional[str] = None


class EventOut(BaseModel):
    id: int
    name: str
    event_date: Optional[str]
    created_at: str


class EventWithParticipantsOut(EventOut):
    participants: list[ParticipantOut]


class AddParticipantRequest(BaseModel):
    participant_id: int


class EventParticipantLinkOut(BaseModel):
    event_id: int
    participant_id: int


class ReceiptCreatedOut(BaseModel):
    id: int
    image_path: str


class EventReceiptOut(BaseModel):
    id: int
    payer_participant_id: int
    payer_name: str
    total_amount: float
    image_path: str
    uploaded_at: str


class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)


class ItemCreatedOut(BaseModel):
    id: int
    description: str
    price: float


class AssignmentIn(BaseModel):
    participant_id: int
    share: float = Field(gt=0)


class AssignmentOut(BaseModel):
    participant_id: int
    participant_name: str
    share: float


class ItemOut(BaseModel):
    id: int
    description: str
    price: float
    quantity: int
    assignments: list[AssignmentOut] = []


class ReceiptWithItemsOut(BaseModel):
    id: int
    event_id: int
    image_path: str
    paid_by: int
    total_amount: float
    uploaded_at: str
    items: list[ItemOut]


class EventBalanceOut(BaseModel):
    participant_id: int
    participant_name: str
    total_paid: float
    total_consumed: float
    net_balance: float


class OverallBalanceOut(BaseModel):
    participant_id: int
    participant_name: str
    total_paid_all_events: float
    total_consumed_all_events: float
    total_net_balance: float


class ProposedItemOut(BaseModel):
    description: str
    price: float
    quantity: int


class ExtractionProposalOut(BaseModel):
    receipt_id: int
    items: list[ProposedItemOut]
    receipt_total: float
    warnings: list[str]
    tax_amount: float


class DataClearedOut(BaseModel):
    status: str


# --- Participants -------------------------------------------------------------


@app.post("/participants", response_model=IdResponse, status_code=201)
def create_participant(payload: ParticipantCreate) -> IdResponse:
    participant_id = db.create_participant(payload.name)
    return IdResponse(id=participant_id)


@app.get("/participants", response_model=list[ParticipantOut])
def list_participants() -> list[dict]:
    return db.list_participants()


@app.delete("/participants/{participant_id}", status_code=204)
def delete_participant(participant_id: int) -> None:
    """Deletes a participant, unless they have financial history (they paid
    a receipt or have item assignments) — deleting them then would corrupt
    the ledger, so that case is rejected with 409 instead of the generic
    404/422 mapping used elsewhere."""
    try:
        db.delete_participant(participant_id)
    except ValueError as error:
        message = str(error)
        if "does not exist" in message:
            raise HTTPException(status_code=404, detail=message) from error
        if "cannot be deleted" in message:
            raise HTTPException(status_code=409, detail=message) from error
        raise value_error_to_http(error) from error


# --- Events ---------------------------------------------------------------------


@app.post("/events", response_model=IdResponse, status_code=201)
def create_event(payload: EventCreate) -> IdResponse:
    event_id = db.create_event(payload.name, payload.event_date)
    return IdResponse(id=event_id)


@app.get("/events", response_model=list[EventOut])
def list_events() -> list[dict]:
    return db.list_events()


@app.get("/events/{event_id}", response_model=EventWithParticipantsOut)
def get_event(event_id: int) -> dict:
    event = db.get_event_with_participants(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id} does not exist")
    return event


@app.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int) -> None:
    """Deletes an event and all its dependent data (receipts, items,
    assignments, event-participant links); cascade is handled inside
    db.delete_event."""
    try:
        db.delete_event(event_id)
    except ValueError as error:
        raise value_error_to_http(error) from error


@app.post(
    "/events/{event_id}/participants",
    response_model=EventParticipantLinkOut,
    status_code=201,
)
def add_participant_to_event(
    event_id: int, payload: AddParticipantRequest
) -> EventParticipantLinkOut:
    try:
        db.add_participant_to_event(event_id, payload.participant_id)
    except ValueError as error:
        raise value_error_to_http(error) from error
    return EventParticipantLinkOut(event_id=event_id, participant_id=payload.participant_id)


# --- Receipts (image upload) -----------------------------------------------------


@app.post(
    "/events/{event_id}/receipts",
    response_model=ReceiptCreatedOut,
    status_code=201,
)
def upload_receipt(
    event_id: int,
    payer_participant_id: Annotated[int, Form()],
    total: Annotated[float, Form(gt=0)],
    image: UploadFile = File(...),
) -> ReceiptCreatedOut:
    """Upload endpoint: stores the receipt image and its metadata ONLY.
    No OCR/vision/item recognition happens here (out of scope for Phase 1).

    Note: form fields are declared individually rather than via a single
    Pydantic model, because this FastAPI version does not flatten a
    Form()-annotated BaseModel into independent multipart fields when an
    UploadFile is also present (it instead expects one nested field named
    after the parameter). Each field below is still parsed and validated
    through FastAPI's Pydantic-backed Form() machinery (required, gt=0)."""
    image_path = save_receipt_image(image)

    try:
        receipt_id = db.create_receipt(
            event_id=event_id,
            payer_participant_id=payer_participant_id,
            total=total,
            image_path=image_path,
        )
    except ValueError as error:
        raise value_error_to_http(error) from error

    return ReceiptCreatedOut(id=receipt_id, image_path=image_path)


@app.get("/events/{event_id}/receipts", response_model=list[EventReceiptOut])
def list_event_receipts(event_id: int) -> list[dict]:
    try:
        return db.list_event_receipts(event_id)
    except ValueError as error:
        raise value_error_to_http(error) from error


@app.get("/receipts/{receipt_id}", response_model=ReceiptWithItemsOut)
def get_receipt(receipt_id: int) -> dict:
    receipt = db.get_receipt_with_items(receipt_id)
    if receipt is None:
        raise HTTPException(
            status_code=404, detail=f"Receipt {receipt_id} does not exist"
        )
    return receipt


@app.post(
    "/receipts/{receipt_id}/extract",
    response_model=ExtractionProposalOut,
)
def extract_receipt(receipt_id: int) -> ExtractionProposalOut:
    """Propose items for a receipt by running the Phase 2 vision extractor
    over its already-uploaded image.

    Key invariant: this endpoint only PROPOSES items — it never persists
    anything. Saving proposed items still requires a human review step
    through the existing `POST /receipts/{receipt_id}/items` (manual
    capture), which remains the single source of truth for what actually
    gets billed.
    """
    receipt = db.get_receipt_with_items(receipt_id)
    if receipt is None:
        raise HTTPException(
            status_code=404, detail=f"Receipt {receipt_id} does not exist"
        )

    image_path = receipt["image_path"]
    if not image_path:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Receipt {receipt_id} has no stored image; "
                "use manual item capture instead."
            ),
        )

    try:
        result = vision.extract_receipt_items(image_path)
    except vision.ExtractionError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return ExtractionProposalOut(
        receipt_id=receipt_id,
        items=[
            ProposedItemOut(
                description=item.description,
                price=item.price,
                quantity=item.quantity,
            )
            for item in result.items
        ],
        receipt_total=result.receipt_total,
        warnings=result.warnings,
        tax_amount=result.tax_amount,
    )


# --- Items (manual capture) -------------------------------------------------------


@app.post(
    "/receipts/{receipt_id}/items",
    response_model=list[ItemCreatedOut],
    status_code=201,
)
def add_items(
    receipt_id: int, payload: Union[ItemCreate, list[ItemCreate]]
) -> list[ItemCreatedOut]:
    """Accepts either a single item object or a list of items in the JSON body."""
    items = payload if isinstance(payload, list) else [payload]

    created: list[ItemCreatedOut] = []
    for item in items:
        try:
            item_id = db.add_item(receipt_id, item.name, item.price)
        except ValueError as error:
            raise value_error_to_http(error) from error
        created.append(ItemCreatedOut(id=item_id, description=item.name, price=item.price))

    return created


# --- Item assignments -----------------------------------------------------------


@app.put("/items/{item_id}/assignments", response_model=list[AssignmentOut])
def set_item_assignments(
    item_id: int, payload: list[AssignmentIn]
) -> list[dict]:
    """Replace-semantics: the given assignments fully supersede whatever was
    assigned to this item before. Pydantic validates shape and share > 0;
    db.assign_item validates the invariants that need DB state (item
    exists, shares sum to 1.0, no duplicate participants, participants
    belong to the item's event)."""
    assignments = [
        {"participant_id": a.participant_id, "share": a.share} for a in payload
    ]
    try:
        db.assign_item(item_id, assignments)
    except ValueError as error:
        raise value_error_to_http(error) from error

    return db.get_item_assignments(item_id)


@app.get("/items/{item_id}/assignments", response_model=list[AssignmentOut])
def get_item_assignments(item_id: int) -> list[dict]:
    try:
        return db.get_item_assignments(item_id)
    except ValueError as error:
        raise value_error_to_http(error) from error


# --- Balances (Day 5) ------------------------------------------------------------


@app.get("/events/{event_id}/balances", response_model=list[EventBalanceOut])
def get_event_balances(event_id: int) -> list[dict]:
    try:
        return db.get_event_balances(event_id)
    except ValueError as error:
        raise value_error_to_http(error) from error


@app.get("/balances", response_model=list[OverallBalanceOut])
def get_overall_balances() -> list[dict]:
    return db.get_overall_balances()


# --- Destructive full reset -------------------------------------------------------


@app.delete("/data", response_model=DataClearedOut)
def clear_all_data() -> DataClearedOut:
    """Full destructive reset: wipes every table via db.clear_all_data() and
    removes stored upload files so no orphaned receipt images remain. There
    is no confirmation step at this layer — the caller (UI/CLI) is expected
    to gate this behind an explicit user confirmation before calling it."""
    db.clear_all_data()
    clear_upload_dir()
    return DataClearedOut(status="all data deleted")
