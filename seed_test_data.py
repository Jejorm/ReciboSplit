"""
Seeds Events 1 and 2 of the Phase 1 acceptance scenario (see
PROJECT_STATUS.md) and validates the full pyturso write + push()/pull()
round trip against Turso Cloud.

Run with: uv run python seed_test_data.py
Requires TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in your .env.

Idempotency strategy: each event name is treated as the natural key for its
seed. Before inserting, any existing event with that name (and everything
cascading from it: event_participants, receipts, items, item_assignments) is
deleted, so the script can be re-run safely — for either event independently.

Naming convention: event names are stored ASCII-normalized (no accents), a
precedent set by Event 1 ("Asado sabado" instead of "Asado sábado" as it
appears in PROJECT_STATUS.md). Event 2 follows the same rule: "Dia de playa"
instead of "Día de playa".
"""

import glob
import os

import turso.sync
from dotenv import load_dotenv

EVENT_NAME = "Asado sabado"
EVENT_2_NAME = "Dia de playa"
VERIFY_DB_PATH = "recibosplit_verify.db"

load_dotenv()

db = turso.sync.connect(
    "recibosplit.db",
    remote_url=os.environ["TURSO_DATABASE_URL"],
    auth_token=os.environ["TURSO_AUTH_TOKEN"],
)
db.pull()

# --- Clean up any previous run of this seed (idempotency) --------------------
for name in (EVENT_NAME, EVENT_2_NAME):
    existing = db.execute(
        "SELECT id FROM events WHERE name = ?", (name,)
    ).fetchall()
    for (event_id,) in existing:
        # Gotcha: PRAGMA foreign_keys is OFF on pyturso connections, so
        # schema.sql's ON DELETE CASCADE does not fire — cascade explicitly,
        # same pattern as db.py's delete_event().
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

# Participants are shared across events; only remove them if this is a clean
# re-run and nothing else references them, to avoid orphaning other events'
# data. For this seed script we recreate them if missing, but do not delete
# participants that might be reused elsewhere.
db.commit()

# --- Participants -------------------------------------------------------------
participant_ids = {}
for name in ("Ana", "Bruno", "Carla"):
    row = db.execute(
        "SELECT id FROM participants WHERE name = ?", (name,)
    ).fetchone()
    if row is None:
        db.execute("INSERT INTO participants (name) VALUES (?)", (name,))
        participant_id = db.execute(
            "SELECT id FROM participants WHERE name = ?", (name,)
        ).fetchone()[0]
    else:
        participant_id = row[0]
    participant_ids[name] = participant_id

# --- Event ----------------------------------------------------------------
db.execute(
    "INSERT INTO events (name, event_date) VALUES (?, ?)",
    (EVENT_NAME, "2026-07-11"),
)
event_id = db.execute(
    "SELECT id FROM events WHERE name = ?", (EVENT_NAME,)
).fetchone()[0]

for name in ("Ana", "Bruno", "Carla"):
    db.execute(
        "INSERT INTO event_participants (event_id, participant_id) VALUES (?, ?)",
        (event_id, participant_ids[name]),
    )

# --- Receipt (paid by Ana, total $90) -----------------------------------------
db.execute(
    "INSERT INTO receipts (event_id, image_path, paid_by, total_amount) "
    "VALUES (?, ?, ?, ?)",
    (event_id, "seed/asado_sabado.jpg", participant_ids["Ana"], 90.0),
)
receipt_id = db.execute(
    "SELECT id FROM receipts WHERE event_id = ? AND paid_by = ?",
    (event_id, participant_ids["Ana"]),
).fetchone()[0]


def validate_shares(shares: dict[str, float]) -> None:
    """Guard: sum of shares for an item must equal 1.0 within a float tolerance."""
    total = sum(shares.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Item assignment shares must sum to 1.0, got {total}")


def insert_item_with_assignments(
    receipt_id: int, description: str, price: float, shares: dict[str, float]
) -> int:
    validate_shares(shares)
    db.execute(
        "INSERT INTO items (receipt_id, description, price) VALUES (?, ?, ?)",
        (receipt_id, description, price),
    )
    item_id = db.execute(
        "SELECT id FROM items WHERE receipt_id = ? AND description = ?",
        (receipt_id, description),
    ).fetchone()[0]
    for name, share in shares.items():
        db.execute(
            "INSERT INTO item_assignments (item_id, participant_id, share) "
            "VALUES (?, ?, ?)",
            (item_id, participant_ids[name], share),
        )
    return item_id


# Item "Carne" $60, split evenly among Ana/Bruno/Carla (share 1/3 each)
insert_item_with_assignments(
    receipt_id,
    "Carne",
    60.0,
    {"Ana": 1 / 3, "Bruno": 1 / 3, "Carla": 1 / 3},
)

# Item "Bebidas" $30, split evenly between Bruno/Carla only (share 1/2 each)
insert_item_with_assignments(
    receipt_id,
    "Bebidas",
    30.0,
    {"Bruno": 1 / 2, "Carla": 1 / 2},
)

# --- Event 2 ---------------------------------------------------------------
# Participants: Bruno and Carla only (Ana is intentionally not included).
db.execute(
    "INSERT INTO events (name, event_date) VALUES (?, ?)",
    (EVENT_2_NAME, "2026-07-12"),
)
event_2_id = db.execute(
    "SELECT id FROM events WHERE name = ?", (EVENT_2_NAME,)
).fetchone()[0]

for name in ("Bruno", "Carla"):
    db.execute(
        "INSERT INTO event_participants (event_id, participant_id) VALUES (?, ?)",
        (event_2_id, participant_ids[name]),
    )

# --- Receipt (paid by Carla, total $40, no image) -----------------------------
# schema.sql declares receipts.image_path TEXT NOT NULL, so a bare NULL is not
# an option without a migration. Since this is a one-off seed case (not a
# recurring product need), we use "" (empty string) as the sentinel for "no
# image was uploaded for this receipt" instead of a fake/misleading path. If
# "no image" becomes a real product requirement, image_path should be made
# nullable via a numbered migration + schema.sql update at that point.
db.execute(
    "INSERT INTO receipts (event_id, image_path, paid_by, total_amount) "
    "VALUES (?, ?, ?, ?)",
    (event_2_id, "", participant_ids["Carla"], 40.0),
)
receipt_2_id = db.execute(
    "SELECT id FROM receipts WHERE event_id = ? AND paid_by = ?",
    (event_2_id, participant_ids["Carla"]),
).fetchone()[0]

# Item "Snacks" $40, split evenly between Bruno/Carla (share 1/2 each)
insert_item_with_assignments(
    receipt_2_id,
    "Snacks",
    40.0,
    {"Bruno": 1 / 2, "Carla": 1 / 2},
)

db.commit()
db.push()
print("Write transaction committed and pushed to Turso Cloud.")

# --- Validate round trip: read balances through the same connection ----------
name_by_id = {v: k for k, v in participant_ids.items()}


def print_event_balances(label: str, ev_id: int) -> None:
    print(f"\nevent_balances for '{label}' (event_id={ev_id}, same connection, post-push):")
    rows = db.execute(
        "SELECT event_id, participant_id, total_paid, total_consumed, net_balance "
        "FROM event_balances WHERE event_id = ? ORDER BY participant_id",
        (ev_id,),
    ).fetchall()
    print(f"{'Participant':<12}{'Total paid':>12}{'Total consumed':>16}{'Net balance':>14}")
    for _, participant_id, total_paid, total_consumed, net_balance in rows:
        print(
            f"{name_by_id[participant_id]:<12}{total_paid:>12.2f}"
            f"{total_consumed:>16.2f}{net_balance:>14.2f}"
        )


print_event_balances(EVENT_NAME, event_id)
print_event_balances(EVENT_2_NAME, event_2_id)

print("\noverall_balances (same connection, post-push):")
overall_rows = db.execute(
    "SELECT participant_id, total_paid_all_events, total_consumed_all_events, "
    "total_net_balance FROM overall_balances ORDER BY participant_id"
).fetchall()
print(f"{'Participant':<12}{'Total paid':>12}{'Total consumed':>16}{'Net balance':>14}")
for participant_id, total_paid, total_consumed, net_balance in overall_rows:
    print(
        f"{name_by_id[participant_id]:<12}{total_paid:>12.2f}"
        f"{total_consumed:>16.2f}{net_balance:>14.2f}"
    )

# --- Validate round trip against the remote: fresh connection + pull ---------
print("\nOpening a fresh connection and pulling from remote to confirm sync...")
db2 = turso.sync.connect(
    VERIFY_DB_PATH,
    remote_url=os.environ["TURSO_DATABASE_URL"],
    auth_token=os.environ["TURSO_AUTH_TOKEN"],
)
db2.pull()

remote_participants = db2.execute(
    "SELECT name FROM participants WHERE name IN ('Ana', 'Bruno', 'Carla') "
    "ORDER BY name"
).fetchall()
remote_items_event_1 = db2.execute(
    "SELECT description, price FROM items i "
    "JOIN receipts r ON r.id = i.receipt_id "
    "JOIN events e ON e.id = r.event_id "
    "WHERE e.name = ? ORDER BY description",
    (EVENT_NAME,),
).fetchall()
remote_items_event_2 = db2.execute(
    "SELECT description, price FROM items i "
    "JOIN receipts r ON r.id = i.receipt_id "
    "JOIN events e ON e.id = r.event_id "
    "WHERE e.name = ? ORDER BY description",
    (EVENT_2_NAME,),
).fetchall()

print(f"Remote participants found: {[r[0] for r in remote_participants]}")
print(f"Remote items found for '{EVENT_NAME}': {remote_items_event_1}")
print(f"Remote items found for '{EVENT_2_NAME}': {remote_items_event_2}")

if (
    len(remote_participants) == 3
    and len(remote_items_event_1) == 2
    and len(remote_items_event_2) == 1
):
    print("\nRemote round trip CONFIRMED: data reached Turso Cloud.")
else:
    print("\nWARNING: remote data does not match what was written locally.")

db2.close()

# Throwaway verification replica: remove its local files so it never lingers
# in the working tree (it is not the app's real local replica).
for path in glob.glob(f"{VERIFY_DB_PATH}*"):
    os.remove(path)

# --- Summary -------------------------------------------------------------
print("\n--- Summary ---")
print(f"Event 1: '{EVENT_NAME}' (id={event_id})")
print(f"Event 2: '{EVENT_2_NAME}' (id={event_2_id})")
print("Rows inserted this run: 3 participants (if not already present), "
      "2 events, 5 event_participants (3 + 2), 2 receipts, 3 items "
      "(2 + 1), 7 item_assignments (5 + 2)")
print("push(): completed without error")
print("pull() round trip against remote: confirmed above")
