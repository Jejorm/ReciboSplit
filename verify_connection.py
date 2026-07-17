"""
One-off sanity check: confirms the local pyturso replica can sync with
Turso Cloud and that schema.sql was loaded correctly.

Run with: uv run python verify_connection.py
Requires TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in your .env.
"""

import os

import turso.sync
from dotenv import load_dotenv

load_dotenv()

db = turso.sync.connect(
    "recibosplit.db",
    remote_url=os.environ["TURSO_DATABASE_URL"],
    auth_token=os.environ["TURSO_AUTH_TOKEN"],
)
db.pull()

print("Tables and views found:")
for row in db.execute(
    "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name"
):
    print(f"  - {row}")

expected = {
    "participants",
    "events",
    "event_participants",
    "receipts",
    "items",
    "item_assignments",
    "event_balances",
    "overall_balances",
}
found = {
    row[0]
    for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    )
}

missing = expected - found
if missing:
    print(f"\nMISSING: {missing} — re-run `turso db shell recibosplit < schema.sql`")
else:
    print("\nAll expected tables and views are present. Setup looks good.")