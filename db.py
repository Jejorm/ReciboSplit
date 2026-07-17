"""
Data-access layer for ReciboSplit, backed by Turso via the pyturso embedded-
replica model (see CLAUDE.md and schema.sql). FastAPI endpoints (api-agent)
call into this module instead of writing SQL directly.

Connection lifecycle:
- `get_db()` lazily creates a single shared connection for the whole server
  process, pulling from remote once on first use.
- Call `init_db()` explicitly at application startup (e.g. FastAPI lifespan)
  to establish the connection and pull eagerly, rather than relying on the
  first request to pay that cost.
- Every write function commits its transaction and then calls `db.push()`
  before returning, so the remote is never left stale after a successful
  write.

Local-only mode (for tests): if `TURSO_DATABASE_URL` or `TURSO_AUTH_TOKEN` is
not set, `init_db()` opens a plain local connection (`turso.connect()`, no
sync) against `RECIBOSPLIT_DB_PATH` instead of a `turso.sync` replica. In this
mode `db.push()`/`db.pull()` are no-ops — see `_attach_noop_sync()` — so every
existing write/read function in this module keeps calling `db.push()` /
`db.pull()` unchanged, with no `if local_mode` branches scattered through
business logic. This lets a pytest suite point `RECIBOSPLIT_DB_PATH` at a
throwaway temp file, load schema.sql into it via `load_schema()` (see its
docstring for a pyturso executescript() gotcha with schema.sql's accented
comments), and exercise the full read/write API fully offline, with zero
risk to the shared remote.
Call `close_db()` between test sessions to drop the shared connection so the
next `get_db()`/`init_db()` call opens a fresh file.

Scope: participants, events, event_participants, receipts, items,
item_assignments (assignment writes/reads, delete helpers), and balance
reads (get_event_balances / get_overall_balances — plain SELECTs from the
event_balances / overall_balances views defined in schema.sql; the
calculation itself lives only in those views, never in Python).

Gotcha: `PRAGMA foreign_keys` is OFF by default on pyturso connections, so
schema.sql's `ON DELETE CASCADE` clauses do not fire automatically. All
delete_* functions below cascade explicitly in SQL instead of relying on it.
"""

import os
import re
from typing import Optional, Union

import turso
import turso.sync
from dotenv import load_dotenv

load_dotenv()

DBConnection = Union["turso.Connection", "turso.sync.Connection"]

_db: Optional[DBConnection] = None


def _local_only_mode() -> bool:
    """True when Turso Cloud credentials are not configured (either
    TURSO_DATABASE_URL or TURSO_AUTH_TOKEN missing from the environment).
    In that case init_db() falls back to a plain, non-syncing local
    connection instead of a turso.sync replica."""
    return not (
        os.environ.get("TURSO_DATABASE_URL") and os.environ.get("TURSO_AUTH_TOKEN")
    )


def _attach_noop_sync(conn: "turso.Connection") -> None:
    """Attach no-op push()/pull() methods onto a plain (non-sync) connection
    object. This is what makes local-only mode transparent: every call site
    in this module already says `db.push()` / `db.pull()`, so instead of
    guarding each one with `if not local_only: ...`, we make those methods
    exist (and do nothing) on the connection itself."""
    conn.push = lambda: None  # type: ignore[attr-defined]
    conn.pull = lambda: None  # type: ignore[attr-defined]


def init_db() -> DBConnection:
    """Create the shared connection (if not already created) and pull from
    remote. Call this once at application startup.

    The local replica filename is configurable via the RECIBOSPLIT_DB_PATH
    env var (default: "recibosplit.db"). This exists so a second process
    (e.g. the MCP server in mcp_server.py) can sync its own replica file
    against the same Turso Cloud database, instead of contending for the
    exclusive file lock that turso.sync holds on a single replica file.

    See the module docstring for local-only mode (no Turso Cloud
    credentials): in that case this opens a plain local connection instead,
    with push()/pull() turned into no-ops."""
    global _db
    if _db is None:
        db_path = os.environ.get("RECIBOSPLIT_DB_PATH", "recibosplit.db")
        if _local_only_mode():
            _db = turso.connect(db_path)
            _attach_noop_sync(_db)
        else:
            _db = turso.sync.connect(
                db_path,
                remote_url=os.environ["TURSO_DATABASE_URL"],
                auth_token=os.environ["TURSO_AUTH_TOKEN"],
            )
        _db.pull()
    return _db


def get_db() -> DBConnection:
    """Return the shared connection, creating it via init_db() if needed.
    Safe to call from any request handler."""
    if _db is None:
        return init_db()
    return _db


def load_schema(conn: DBConnection, schema_path: str = "schema.sql") -> None:
    """Load schema.sql (or another SQL file) into `conn` via executescript().
    Intended for tests bootstrapping a fresh local-only temp file: e.g.
    `db.load_schema(db.init_db(), "schema.sql")`.

    Gotcha (pyturso 0.6.1): `Connection.executescript()` tracks its position
    in the script with a byte offset returned by the underlying parser, but
    re-slices the *Python str* (character-indexed) with it between
    statements. schema.sql's Spanish comments contain multi-byte UTF-8
    accented characters (e.g. "línea", "sábado"), which desyncs that byte
    offset from the string index and corrupts the next statement's text
    (observed as spurious "syntax error near ..." with a leading character
    or two silently dropped) as soon as it accumulates past an accented
    comment. Since schema.sql's only non-ASCII bytes live in `--` comments,
    the fix here is to strip `--` comments (both whole-line and trailing)
    before calling executescript(), rather than editing schema.sql itself
    (which is the source of truth and intentionally in Spanish)."""
    with open(schema_path, "r", encoding="utf-8") as f:
        raw_sql = f.read()
    ascii_safe_sql = re.sub(r"--[^\n]*", "", raw_sql)
    conn.executescript(ascii_safe_sql)


def close_db() -> None:
    """Close the shared connection (if any) and clear the module-level
    reference, so the next get_db()/init_db() call opens a fresh one.

    Intended for test suites: point RECIBOSPLIT_DB_PATH (and, for local-only
    mode, unset/leave unset TURSO_DATABASE_URL / TURSO_AUTH_TOKEN) at a new
    temp file per test session, call close_db() first, then init_db()."""
    global _db
    if _db is not None:
        _db.close()
        _db = None


# --- Write functions --------------------------------------------------------


def create_participant(name: str) -> int:
    """Insert a new participant and return its id."""
    db = get_db()
    db.execute("INSERT INTO participants (name) VALUES (?)", (name,))
    db.commit()
    db.push()
    return db.execute(
        "SELECT id FROM participants WHERE name = ? ORDER BY id DESC LIMIT 1",
        (name,),
    ).fetchone()[0]


def create_event(name: str, event_date: Optional[str] = None) -> int:
    """Insert a new event and return its id. `event_date` is an optional
    ISO date string (e.g. '2026-07-11'), matching schema.sql's TEXT column."""
    db = get_db()
    db.execute(
        "INSERT INTO events (name, event_date) VALUES (?, ?)",
        (name, event_date),
    )
    db.commit()
    db.push()
    return db.execute(
        "SELECT id FROM events WHERE name = ? ORDER BY id DESC LIMIT 1",
        (name,),
    ).fetchone()[0]


def add_participant_to_event(event_id: int, participant_id: int) -> None:
    """Link a participant to an event. Validates both FK targets exist
    before inserting, raising ValueError with a clear message otherwise."""
    db = get_db()

    if db.execute(
        "SELECT 1 FROM events WHERE id = ?", (event_id,)
    ).fetchone() is None:
        raise ValueError(f"Event {event_id} does not exist")

    if db.execute(
        "SELECT 1 FROM participants WHERE id = ?", (participant_id,)
    ).fetchone() is None:
        raise ValueError(f"Participant {participant_id} does not exist")

    db.execute(
        "INSERT INTO event_participants (event_id, participant_id) VALUES (?, ?)",
        (event_id, participant_id),
    )
    db.commit()
    db.push()


def create_receipt(
    event_id: int, payer_participant_id: int, total: float, image_path: str
) -> int:
    """Insert a receipt for an event and return its id. Validates that the
    event exists and that the payer is a participant of that event (the
    schema only guarantees the payer is *some* participant via the FK; the
    "must belong to this event" rule is an application-level invariant)."""
    db = get_db()

    if db.execute(
        "SELECT 1 FROM events WHERE id = ?", (event_id,)
    ).fetchone() is None:
        raise ValueError(f"Event {event_id} does not exist")

    if db.execute(
        "SELECT 1 FROM participants WHERE id = ?", (payer_participant_id,)
    ).fetchone() is None:
        raise ValueError(f"Participant {payer_participant_id} does not exist")

    if db.execute(
        "SELECT 1 FROM event_participants WHERE event_id = ? AND participant_id = ?",
        (event_id, payer_participant_id),
    ).fetchone() is None:
        raise ValueError(
            f"Participant {payer_participant_id} is not a participant of "
            f"event {event_id}; add them via add_participant_to_event() first"
        )

    db.execute(
        "INSERT INTO receipts (event_id, image_path, paid_by, total_amount) "
        "VALUES (?, ?, ?, ?)",
        (event_id, image_path, payer_participant_id, total),
    )
    db.commit()
    db.push()
    return db.execute(
        "SELECT id FROM receipts WHERE event_id = ? AND paid_by = ? "
        "ORDER BY id DESC LIMIT 1",
        (event_id, payer_participant_id),
    ).fetchone()[0]


def validate_shares(shares: list[float]) -> None:
    """Guard: sum of `share` values for a single item must equal 1.0 within a
    float tolerance. Adapted from the pattern established in
    seed_test_data.py (there keyed by participant name; here it operates on
    the raw share values so it can be reused for any list of assignments)."""
    total = sum(shares)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Item assignment shares must sum to 1.0, got {total}")


def assign_item(item_id: int, assignments: list[dict]) -> None:
    """Replace all assignments for `item_id` with the given set in a single
    transaction, then push.

    `assignments` is a list of {"participant_id": int, "share": float}.

    Semantics: REPLACE. Any existing item_assignments rows for this item_id
    are deleted before inserting the new set, so calling this twice is
    idempotent — the second call's assignments fully supersede the first's.

    Validates (raises ValueError, no partial writes):
    - the item exists
    - `assignments` is non-empty
    - no duplicate participant_id
    - every share > 0
    - shares sum to 1.0 within a float tolerance (validate_shares)
    - every assigned participant is an event_participant of the event that
      owns this item (via item -> receipt -> event)
    """
    db = get_db()

    item_row = db.execute(
        "SELECT r.event_id FROM items i "
        "JOIN receipts r ON r.id = i.receipt_id "
        "WHERE i.id = ?",
        (item_id,),
    ).fetchone()
    if item_row is None:
        raise ValueError(f"Item {item_id} does not exist")
    event_id = item_row[0]

    if not assignments:
        raise ValueError(f"At least one assignment is required for item {item_id}")

    participant_ids = [a["participant_id"] for a in assignments]
    if len(participant_ids) != len(set(participant_ids)):
        raise ValueError(
            f"Duplicate participant ids in assignments for item {item_id}"
        )

    for a in assignments:
        if a["share"] <= 0:
            raise ValueError(
                f"Share for participant {a['participant_id']} must be "
                f"greater than 0, got {a['share']}"
            )

    validate_shares([a["share"] for a in assignments])

    for pid in participant_ids:
        if db.execute(
            "SELECT 1 FROM event_participants WHERE event_id = ? AND participant_id = ?",
            (event_id, pid),
        ).fetchone() is None:
            raise ValueError(
                f"Participant {pid} is not a participant of event {event_id}; "
                f"cannot assign item {item_id} to them"
            )

    db.execute("DELETE FROM item_assignments WHERE item_id = ?", (item_id,))
    for a in assignments:
        db.execute(
            "INSERT INTO item_assignments (item_id, participant_id, share) "
            "VALUES (?, ?, ?)",
            (item_id, a["participant_id"], a["share"]),
        )
    db.commit()
    db.push()


def add_item(receipt_id: int, name: str, price: float) -> int:
    """Insert an item (schema column is `description`) for a receipt and
    return its id. Validates the receipt exists."""
    db = get_db()

    if db.execute(
        "SELECT 1 FROM receipts WHERE id = ?", (receipt_id,)
    ).fetchone() is None:
        raise ValueError(f"Receipt {receipt_id} does not exist")

    db.execute(
        "INSERT INTO items (receipt_id, description, price) VALUES (?, ?, ?)",
        (receipt_id, name, price),
    )
    db.commit()
    db.push()
    return db.execute(
        "SELECT id FROM items WHERE receipt_id = ? AND description = ? "
        "ORDER BY id DESC LIMIT 1",
        (receipt_id, name),
    ).fetchone()[0]


# --- Delete helpers -----------------------------------------------------------
#
# Gotcha: schema.sql declares `ON DELETE CASCADE` on several foreign keys, but
# pyturso connections do NOT enable `PRAGMA foreign_keys` by default (verified
# empirically: a fresh connection reports `PRAGMA foreign_keys` = 0). Since
# that pragma is per-connection and not persisted in the database file, and
# this app/its scripts open several independent connections (main.py,
# seed_test_data.py, verify_connection.py, MCP server), relying on it being
# turned on everywhere is fragile. These helpers therefore cascade explicitly
# in Python/SQL rather than assuming the schema's ON DELETE CASCADE fires.


def delete_item(item_id: int) -> None:
    """Delete an item and its item_assignments. Raises ValueError if the
    item does not exist."""
    db = get_db()
    if db.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone() is None:
        raise ValueError(f"Item {item_id} does not exist")

    db.execute("DELETE FROM item_assignments WHERE item_id = ?", (item_id,))
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()
    db.push()


def delete_receipt(receipt_id: int) -> None:
    """Delete a receipt and everything under it (items, item_assignments).
    Raises ValueError if the receipt does not exist."""
    db = get_db()
    if db.execute(
        "SELECT 1 FROM receipts WHERE id = ?", (receipt_id,)
    ).fetchone() is None:
        raise ValueError(f"Receipt {receipt_id} does not exist")

    db.execute(
        "DELETE FROM item_assignments WHERE item_id IN "
        "(SELECT id FROM items WHERE receipt_id = ?)",
        (receipt_id,),
    )
    db.execute("DELETE FROM items WHERE receipt_id = ?", (receipt_id,))
    db.execute("DELETE FROM receipts WHERE id = ?", (receipt_id,))
    db.commit()
    db.push()


def delete_event(event_id: int) -> None:
    """Delete an event and everything under it (event_participants, receipts,
    items, item_assignments). Raises ValueError if the event does not
    exist."""
    db = get_db()
    if db.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone() is None:
        raise ValueError(f"Event {event_id} does not exist")

    db.execute(
        "DELETE FROM item_assignments WHERE item_id IN ("
        "  SELECT i.id FROM items i "
        "  JOIN receipts r ON r.id = i.receipt_id "
        "  WHERE r.event_id = ?"
        ")",
        (event_id,),
    )
    db.execute(
        "DELETE FROM items WHERE receipt_id IN "
        "(SELECT id FROM receipts WHERE event_id = ?)",
        (event_id,),
    )
    db.execute("DELETE FROM receipts WHERE event_id = ?", (event_id,))
    db.execute("DELETE FROM event_participants WHERE event_id = ?", (event_id,))
    db.execute("DELETE FROM events WHERE id = ?", (event_id,))
    db.commit()
    db.push()


def delete_participant(participant_id: int) -> None:
    """Delete a participant. Raises ValueError if the participant does not
    exist.

    Safe-deletion policy: a participant carries financial history the moment
    they have paid for a receipt (`receipts.paid_by`) or have been assigned
    a share of an item (`item_assignments`) — deleting them in that case
    would silently corrupt past balances. This is REFUSED with a ValueError
    naming the reason.

    A participant with no such history but who is merely linked to one or
    more events (`event_participants`, e.g. added to an event but never
    involved in a receipt/assignment) is safe to remove: those membership
    links are cascade-deleted first, then the participant row.
    """
    db = get_db()
    if db.execute(
        "SELECT 1 FROM participants WHERE id = ?", (participant_id,)
    ).fetchone() is None:
        raise ValueError(f"Participant {participant_id} does not exist")

    if db.execute(
        "SELECT 1 FROM receipts WHERE paid_by = ?", (participant_id,)
    ).fetchone() is not None:
        raise ValueError(
            f"Participant {participant_id} has paid for one or more receipts "
            "and cannot be deleted (would corrupt payment history)"
        )

    if db.execute(
        "SELECT 1 FROM item_assignments WHERE participant_id = ?",
        (participant_id,),
    ).fetchone() is not None:
        raise ValueError(
            f"Participant {participant_id} has one or more item assignments "
            "and cannot be deleted (would corrupt consumption history)"
        )

    db.execute(
        "DELETE FROM event_participants WHERE participant_id = ?",
        (participant_id,),
    )
    db.execute("DELETE FROM participants WHERE id = ?", (participant_id,))
    db.commit()
    db.push()


def clear_all_data() -> None:
    """Destructive full reset of ALL application data (Phase 2 Task 7), used
    by the "delete all data" feature. Deletes every row from every table,
    leaving schema.sql's tables/views/indexes intact — only the data is
    wiped, not the schema itself.

    Same FK-safe-order rationale as the other delete_* helpers above (pyturso
    connections don't enable `PRAGMA foreign_keys`, so ON DELETE CASCADE does
    not fire): item_assignments -> items -> receipts -> event_participants ->
    events -> participants. Idempotent — safe to call on an already-empty
    database."""
    db = get_db()
    db.execute("DELETE FROM item_assignments")
    db.execute("DELETE FROM items")
    db.execute("DELETE FROM receipts")
    db.execute("DELETE FROM event_participants")
    db.execute("DELETE FROM events")
    db.execute("DELETE FROM participants")
    db.commit()
    db.push()


# --- Read functions -----------------------------------------------------------


def list_participants() -> list[dict]:
    """Return all participants as a list of {id, name, created_at} dicts."""
    db = get_db()
    rows = db.execute(
        "SELECT id, name, created_at FROM participants ORDER BY name"
    ).fetchall()
    return [
        {"id": row[0], "name": row[1], "created_at": row[2]} for row in rows
    ]


def list_events() -> list[dict]:
    """Return all events as a list of {id, name, event_date, created_at} dicts."""
    db = get_db()
    rows = db.execute(
        "SELECT id, name, event_date, created_at FROM events ORDER BY id"
    ).fetchall()
    return [
        {
            "id": row[0],
            "name": row[1],
            "event_date": row[2],
            "created_at": row[3],
        }
        for row in rows
    ]


def get_event_with_participants(event_id: int) -> Optional[dict]:
    """Return {id, name, event_date, created_at, participants: [...]} for an
    event, or None if it does not exist."""
    db = get_db()
    event_row = db.execute(
        "SELECT id, name, event_date, created_at FROM events WHERE id = ?",
        (event_id,),
    ).fetchone()
    if event_row is None:
        return None

    participant_rows = db.execute(
        "SELECT p.id, p.name, p.created_at "
        "FROM event_participants ep "
        "JOIN participants p ON p.id = ep.participant_id "
        "WHERE ep.event_id = ? ORDER BY p.name",
        (event_id,),
    ).fetchall()

    return {
        "id": event_row[0],
        "name": event_row[1],
        "event_date": event_row[2],
        "created_at": event_row[3],
        "participants": [
            {"id": row[0], "name": row[1], "created_at": row[2]}
            for row in participant_rows
        ],
    }


def list_event_receipts(event_id: int) -> list[dict]:
    """Return every receipt for `event_id` as a list of {id,
    payer_participant_id, payer_name, total_amount, image_path,
    uploaded_at} dicts, ordered by id. Raises ValueError if the event does
    not exist. An event that exists but has no receipts yet returns an
    empty list. Backs GET /events/{id}/receipts (api-agent).

    Note: schema.sql names the receipt timestamp column `uploaded_at` (not
    `created_at`); the key below matches the actual column, consistent with
    get_receipt_with_items()."""
    db = get_db()
    if db.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone() is None:
        raise ValueError(f"Event {event_id} does not exist")

    rows = db.execute(
        "SELECT r.id, r.paid_by, p.name, r.total_amount, r.image_path, "
        "r.uploaded_at "
        "FROM receipts r "
        "JOIN participants p ON p.id = r.paid_by "
        "WHERE r.event_id = ? ORDER BY r.id",
        (event_id,),
    ).fetchall()
    return [
        {
            "id": row[0],
            "payer_participant_id": row[1],
            "payer_name": row[2],
            "total_amount": row[3],
            "image_path": row[4],
            "uploaded_at": row[5],
        }
        for row in rows
    ]


def get_item_assignments(item_id: int) -> list[dict]:
    """Return the current item_assignments for `item_id` as a list of
    {participant_id, participant_name, share} dicts, ordered by participant
    name. Raises ValueError if the item does not exist. An item that exists
    but has no assignments yet returns an empty list."""
    db = get_db()
    if db.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone() is None:
        raise ValueError(f"Item {item_id} does not exist")

    rows = db.execute(
        "SELECT p.id, p.name, ia.share "
        "FROM item_assignments ia "
        "JOIN participants p ON p.id = ia.participant_id "
        "WHERE ia.item_id = ? ORDER BY p.name",
        (item_id,),
    ).fetchall()
    return [
        {"participant_id": row[0], "participant_name": row[1], "share": row[2]}
        for row in rows
    ]


def get_receipt_with_items(receipt_id: int) -> Optional[dict]:
    """Return {id, event_id, image_path, paid_by, total_amount, uploaded_at,
    items: [...]} for a receipt, or None if it does not exist. Each item in
    `items` includes its own `assignments` list (participant_id,
    participant_name, share) so callers get the full assignment state
    without a second round trip."""
    db = get_db()
    receipt_row = db.execute(
        "SELECT id, event_id, image_path, paid_by, total_amount, uploaded_at "
        "FROM receipts WHERE id = ?",
        (receipt_id,),
    ).fetchone()
    if receipt_row is None:
        return None

    item_rows = db.execute(
        "SELECT id, description, price, quantity FROM items "
        "WHERE receipt_id = ? ORDER BY id",
        (receipt_id,),
    ).fetchall()

    # Single query for all assignments of all items on this receipt, grouped
    # in Python, to avoid an N+1 query per item.
    assignment_rows = db.execute(
        "SELECT ia.item_id, p.id, p.name, ia.share "
        "FROM item_assignments ia "
        "JOIN participants p ON p.id = ia.participant_id "
        "JOIN items i ON i.id = ia.item_id "
        "WHERE i.receipt_id = ? ORDER BY ia.item_id, p.name",
        (receipt_id,),
    ).fetchall()
    assignments_by_item: dict[int, list[dict]] = {}
    for item_id, participant_id, participant_name, share in assignment_rows:
        assignments_by_item.setdefault(item_id, []).append(
            {
                "participant_id": participant_id,
                "participant_name": participant_name,
                "share": share,
            }
        )

    return {
        "id": receipt_row[0],
        "event_id": receipt_row[1],
        "image_path": receipt_row[2],
        "paid_by": receipt_row[3],
        "total_amount": receipt_row[4],
        "uploaded_at": receipt_row[5],
        "items": [
            {
                "id": row[0],
                "description": row[1],
                "price": row[2],
                "quantity": row[3],
                "assignments": assignments_by_item.get(row[0], []),
            }
            for row in item_rows
        ],
    }


# --- Balance reads (Day 4) -----------------------------------------------------
#
# Both functions below are plain SELECTs from the event_balances /
# overall_balances views defined in schema.sql. No arithmetic happens here —
# if the numbers ever look wrong, the fix belongs in the view (via a numbered
# migration + schema.sql update), never as a workaround in this file.


def get_event_balances(event_id: int) -> list[dict]:
    """Return the event_balances view rows for `event_id`, one dict per
    participant of that event: {participant_id, participant_name, total_paid,
    total_consumed, net_balance}. Raises ValueError if the event does not
    exist. An event that exists but has no receipts yet still returns one row
    per participant (total_paid/total_consumed = 0, via the view's COALESCE)."""
    db = get_db()
    if db.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone() is None:
        raise ValueError(f"Event {event_id} does not exist")

    rows = db.execute(
        "SELECT eb.participant_id, p.name, eb.total_paid, eb.total_consumed, "
        "eb.net_balance "
        "FROM event_balances eb "
        "JOIN participants p ON p.id = eb.participant_id "
        "WHERE eb.event_id = ? ORDER BY p.name",
        (event_id,),
    ).fetchall()
    return [
        {
            "participant_id": row[0],
            "participant_name": row[1],
            "total_paid": row[2],
            "total_consumed": row[3],
            "net_balance": row[4],
        }
        for row in rows
    ]


def get_overall_balances() -> list[dict]:
    """Return the overall_balances view rows, one dict per participant with
    any event history: {participant_id, participant_name,
    total_paid_all_events, total_consumed_all_events, total_net_balance}.
    Participants with no event_participants rows at all are absent (the view
    groups from event_balances, which is itself sourced from
    event_participants) — this matches "no history yet" rather than "owes
    zero", which is the correct semantics here."""
    db = get_db()
    rows = db.execute(
        "SELECT ob.participant_id, p.name, ob.total_paid_all_events, "
        "ob.total_consumed_all_events, ob.total_net_balance "
        "FROM overall_balances ob "
        "JOIN participants p ON p.id = ob.participant_id "
        "ORDER BY p.name"
    ).fetchall()
    return [
        {
            "participant_id": row[0],
            "participant_name": row[1],
            "total_paid_all_events": row[2],
            "total_consumed_all_events": row[3],
            "total_net_balance": row[4],
        }
        for row in rows
    ]
