"""
Reusable business-logic helpers for ReciboSplit's API layer (api-agent).
Endpoint handlers in main.py stay thin; anything that is more than "call a
db.py function and translate the result" belongs here.

Phase 1 scope: only file-storage logic for receipt image uploads. Item
recognition (OCR/vision) is intentionally NOT implemented here — see
CLAUDE.md and PROJECT_STATUS.md (Phase 2, out of scope).
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

UPLOAD_DIR = Path("uploads")

# Only these extensions are trusted to pass through as-is; anything else
# (or a missing/empty extension) falls back to a generic binary extension
# rather than trusting the client-supplied filename.
_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".pdf"}


def build_safe_filename(original_filename: str | None) -> str:
    """Build a unique, filesystem-safe filename for a stored upload.

    Never trusts the client-supplied filename directly (path traversal,
    collisions, unsafe characters) — only reuses its extension if it is on
    an explicit allow-list.
    """
    suffix = Path(original_filename).suffix.lower() if original_filename else ""
    if suffix not in _ALLOWED_IMAGE_EXTENSIONS:
        suffix = ".bin"
    return f"{uuid.uuid4().hex}{suffix}"


def save_receipt_image(upload: UploadFile) -> str:
    """Persist an uploaded receipt image under UPLOAD_DIR and return the
    relative path to store in the database. Raises HTTPException(422) if the
    upload is empty.

    This function ONLY stores the file — no OCR/vision/item recognition of
    any kind happens here or anywhere else in this phase.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    contents = upload.file.read()
    if not contents:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    filename = build_safe_filename(upload.filename)
    destination = UPLOAD_DIR / filename
    destination.write_bytes(contents)

    return str(destination)


def clear_upload_dir() -> None:
    """Delete every regular file directly inside UPLOAD_DIR, leaving the
    directory itself in place. Idempotent: a no-op if UPLOAD_DIR does not
    exist or is already empty. Does not recurse into subdirectories.

    Used by the destructive `DELETE /data` reset endpoint so a full data
    wipe does not leave orphaned receipt images on disk.
    """
    if not UPLOAD_DIR.exists():
        return

    for entry in UPLOAD_DIR.iterdir():
        if entry.is_file():
            entry.unlink()


def value_error_to_http(error: ValueError) -> HTTPException:
    """Translate a ValueError raised by db.py into an HTTPException.

    Convention: messages of the form "<X> does not exist" mean a referenced
    resource (event/participant/receipt) was not found -> 404. Any other
    ValueError is an application-level invariant violation (e.g. "payer is
    not a participant of this event") -> 422.
    """
    message = str(error)
    if "does not exist" in message:
        return HTTPException(status_code=404, detail=message)
    return HTTPException(status_code=422, detail=message)
