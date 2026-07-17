"""
Shared pytest fixtures for the ReciboSplit test suite.

Isolation strategy (see CLAUDE.md / db.py's module docstring for the
local-only mode this relies on):

- Every test gets its own throwaway SQLite file under pytest's `tmp_path`
  (a fresh temp dir per test), loaded from schema.sql via `db.load_schema()`
  (never `conn.executescript(open("schema.sql").read())` directly — pyturso
  0.6.1 has a UTF-8 byte-offset bug with schema.sql's Spanish comments).
- `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN` are removed from the environment
  for every test (via monkeypatch.delenv), so `db._local_only_mode()` is
  always True here regardless of what a real `.env` might contain. This
  suite must never touch Turso Cloud or the real recibosplit*.db replicas.
- `db.close_db()` + `db.init_db()` are called around every test so the
  module-level shared connection always points at that test's own file,
  never leaking rows between tests.
- API tests additionally `monkeypatch.chdir(tmp_path)` so the upload
  endpoint's `uploads/` directory (services.py, UPLOAD_DIR = Path("uploads"))
  is created inside the temp dir and never touches the repo's real
  `uploads/`.
"""

import os
from pathlib import Path

import pytest

import db as db_module

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = str(REPO_ROOT / "schema.sql")


@pytest.fixture
def local_db(tmp_path, monkeypatch):
    """Point db.py at a fresh, local-only, schema-loaded SQLite file for a
    single test. Yields the db module itself (call db_module.create_event(),
    etc. directly)."""
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RECIBOSPLIT_DB_PATH", str(db_path))

    db_module.close_db()
    conn = db_module.init_db()
    db_module.load_schema(conn, schema_path=SCHEMA_PATH)

    yield db_module

    db_module.close_db()


@pytest.fixture
def api_client(local_db, tmp_path, monkeypatch):
    """A FastAPI TestClient wired against the same fresh local-only db as
    `local_db`, with cwd redirected to the test's tmp_path so any uploaded
    receipt image lands under a throwaway `uploads/` dir instead of the
    repo's real one. Entered as a context manager so FastAPI's lifespan
    (which calls db.init_db()) actually runs."""
    # Import main.py lazily, only once env/db state is prepared, and only
    # inside the fixture (not at module import time) so every test that
    # imports this module doesn't eagerly import FastAPI's app object.
    from fastapi.testclient import TestClient

    import main as main_module

    monkeypatch.chdir(tmp_path)

    with TestClient(main_module.app) as client:
        yield client


def _make_image_upload(filename: str = "receipt.png", content: bytes = b"\x89PNG\r\n\x1a\nfake") -> dict:
    """A tiny in-memory 'image' upload dict for TestClient's `files=` kwarg.
    Content doesn't need to be a real PNG -- services.py only stores bytes,
    it never decodes/validates image content (no OCR/vision in Phase 1)."""
    return {"image": (filename, content, "image/png")}


@pytest.fixture
def image_upload_files():
    """Factory fixture: call it to get a fresh in-memory image upload dict
    each time (a new receipt upload per call), for TestClient's `files=`
    kwarg. Avoids cross-module imports of a plain helper function, which is
    ambiguous under pytest's default (no `tests/__init__.py`) import mode."""
    return _make_image_upload
