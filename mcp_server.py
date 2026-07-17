"""
Read-only MCP server for ReciboSplit (Day 6 scope). Exposes the balance and
receipt data already computed by db.py / schema.sql as MCP tools so it can be
queried from Claude Code chat (e.g. "how much does each person owe overall?").

HARD CONSTRAINT: turso.sync holds an EXCLUSIVE file lock on its local replica
file. The FastAPI server (main.py/uvicorn) syncs against "recibosplit.db". If
this process opened the same replica file, both processes could not run at
the same time. Instead, this file sets RECIBOSPLIT_DB_PATH to a SEPARATE
replica file (default "recibosplit_mcp.db") before importing db, so this
process syncs its own local copy of the same Turso Cloud database. This must
happen BEFORE `import db`, since db.py reads the env var lazily inside
init_db() but os.environ must already carry our default by the time any
caller (including our own tools) triggers the first connection.

No SQL is written here — every tool below calls straight into db.py's
read functions, mirroring the "endpoints call db.py" convention from
CLAUDE.md / api-agent.

Read-only: this server exposes NO write tools in Phase 1. It only answers
questions; all mutations continue to happen through the FastAPI app.
"""

import os

os.environ.setdefault("RECIBOSPLIT_DB_PATH", "recibosplit_mcp.db")

from mcp.server.fastmcp import FastMCP

import db

mcp = FastMCP("recibosplit")


def _fresh_read() -> None:
    """Pull the latest remote state before every read-only tool call.

    Writes happen exclusively through the FastAPI app (a separate process
    with its own replica file), so this process's local replica can go
    stale between tool calls unless it re-pulls each time."""
    db.get_db().pull()


@mcp.tool()
def list_participants() -> list[dict]:
    """List every participant registered in ReciboSplit, with their id, name,
    and creation timestamp. Use this to look up a participant's id by name,
    or to answer "who is registered" questions."""
    _fresh_read()
    return db.list_participants()


@mcp.tool()
def list_events() -> list[dict]:
    """List every event (e.g. a cookout or a trip), with its id, name,
    optional event_date, and creation timestamp. Use this to look up an
    event's id by name before calling get_event_balances, or to answer
    "what events exist" questions."""
    _fresh_read()
    return db.list_events()


@mcp.tool()
def get_event_balances(event_id: int) -> list[dict]:
    """Get the balance breakdown for ONE specific event: for every
    participant of that event, how much they paid (total_paid), how much
    they consumed (total_consumed), and their net_balance (paid - consumed;
    positive means others owe them, negative means they owe others) for
    THAT EVENT ONLY. Use this to answer questions like "who paid what at
    [event name]" or "who owes whom for [event name]". Look up the event_id
    via list_events() first if you only know the event's name."""
    _fresh_read()
    try:
        return db.get_event_balances(event_id)
    except ValueError as error:
        return [{"error": str(error)}]


@mcp.tool()
def get_overall_balances() -> list[dict]:
    """Get the CUMULATIVE balance across ALL events for every participant:
    total_paid_all_events, total_consumed_all_events, and
    total_net_balance (paid - consumed, summed across every event they have
    participated in). This is the tool to use for "who owes how much
    overall", "what's everyone's total balance", or "who owes whom in
    total" questions that are not scoped to a single event. Net balances
    across all participants always sum to zero."""
    _fresh_read()
    return db.get_overall_balances()


@mcp.tool()
def get_receipt_details(receipt_id: int) -> dict:
    """Get full details for ONE receipt: which event it belongs to, who paid,
    the total amount, the image path on disk, and every item on it together
    with how each item's cost is split across participants (each item's
    `assignments` list gives participant_id, participant_name, and their
    share, e.g. 0.5 for half). Use this to answer "what was on the receipt
    for [event]" or "how was item X split" questions."""
    _fresh_read()
    receipt = db.get_receipt_with_items(receipt_id)
    if receipt is None:
        return {"error": f"Receipt {receipt_id} does not exist"}
    return receipt


if __name__ == "__main__":
    mcp.run()
